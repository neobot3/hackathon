"""Builds and solves a CP-SAT schedule from database rows and the active CBA rules.

Hard constraints: certification, approved unavailability and training, no overlap,
minimum rest, max duty day including travel, max consecutive worked days, consecutive
days off in a rolling window, the 40 h regular-hours average, and the weekly cap on reps
on vacation. The objective grants requested vacation within the cap by seniority, fills
high-priority demands, prefers volunteers, assigns mandatory work in reverse seniority,
keeps reps at the MROs they worked recently, then minimizes premium pay including the
overtime tier per pay period.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ortools.sat.python import cp_model
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from config import settings
from models import (
    Assignment,
    CbaRules,
    DemandResponse,
    MroDemand,
    MroLocation,
    PayPeriod,
    RepTraining,
    RepUnavailability,
    StatutoryHoliday,
    TechRep,
    TravelTime,
)
from schemas import (
    ProposedAssignment,
    ScheduleRunRequest,
    ScheduleRunResponse,
    UnfilledDemand,
)

# Each objective tier outweighs everything below it: granted vacation > coverage by
# priority > volunteer over mandatory > reverse seniority > continuity and home team >
# premium pay.
VACATION_WEIGHT = 10**13
PRIORITY_WEIGHT = 10**10
MANDATORY_PENALTY = 10**9
SENIORITY_STEP = 10**7
MAX_SENIORITY_RANK = 50
# Full weight for a rep whose recent work was all at the demand's MRO.
CONTINUITY_WEIGHT = 10**6
# For a rep based where the team covering the MRO is based.
HOME_TEAM_WEIGHT = 10**6
# The model uses hundredths of an hour and rates in percent, so a premium cost is
# (rate - 100) * hundredths.
HOUR = 100

BLOCKED_MESSAGES = {
    "unavailable": "on approved leave or training",
    "booked": "already booked or short of minimum rest",
    "duty": "over the max duty day once travel is added",
    "declined": "did not accept; set allow_mandatory to assign in reverse seniority",
}


class NoActiveRulesError(Exception):
    pass


@dataclass
class _Pair:
    field_service: bool
    home_team: bool
    mandatory: bool
    travel_hours: float
    paid_hours: float
    # Overtime whatever else is chosen: pattern days off and hours beyond the shift.
    overtime_hours: float
    # Reps without a pattern: regular until the averaging-period budget runs out.
    flexible_hours: float
    flex_ot_rate: int
    fixed_cost: int
    busy_start: datetime
    busy_end: datetime
    pay_period: tuple[date, date]
    averaging_period: tuple[date, date]


def active_rules(db: Session, on: date) -> CbaRules | None:
    stmt = select(CbaRules).where(
        CbaRules.effective_from <= on,
        or_(CbaRules.effective_to.is_(None), CbaRules.effective_to > on),
    )
    return db.scalars(stmt).first()


def _tz(name: str) -> tzinfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return UTC


def home_tz(rep: TechRep, mros: Iterable[MroLocation]) -> tzinfo:
    """Timezone of the MRO at the rep's home base, or UTC when none matches."""
    home = rep.home_base.strip().lower()
    for m in mros:
        if home in {m.location.strip().lower(), (m.airport_code or "").strip().lower()}:
            return _tz(m.timezone)
    return UTC


def _hours_by_local_date(start: datetime, end: datetime, tz: tzinfo) -> dict[date, float]:
    out: dict[date, float] = defaultdict(float)
    cur = start.astimezone(tz)
    end_local = end.astimezone(tz)
    while cur < end_local:
        midnight = datetime.combine(cur.date() + timedelta(days=1), datetime.min.time(), tz)
        seg_end = min(midnight, end_local)
        # Subtract in UTC so DST changes are counted correctly.
        out[cur.date()] += (seg_end.astimezone(UTC) - cur.astimezone(UTC)).total_seconds() / 3600
        cur = seg_end
    return out


def _is_pattern_work_day(rep: TechRep, day: date) -> bool | None:
    """None when the rep has no pattern or cycle start, so work days are unknown."""
    if rep.shift_pattern is None or rep.shift_cycle_start is None:
        return None
    cycle = rep.shift_pattern.cycle
    return cycle[(day - rep.shift_cycle_start).days % len(cycle)] == "W"


def _is_certified(rep: TechRep, demand: MroDemand) -> bool:
    start, end = demand.start_time.date(), demand.end_time.date()
    return any(
        c.aircraft_type_id == demand.aircraft_type_id
        and (c.certified_on is None or c.certified_on <= start)
        and (c.expires_on is None or c.expires_on >= end)
        for c in rep.certifications
    )


def _is_field_service(rep: TechRep, mro: MroLocation) -> bool:
    home = rep.home_base.strip().lower()
    local = {mro.location.strip().lower()}
    if mro.airport_code:
        local.add(mro.airport_code.strip().lower())
    return home not in local


def is_home_team(rep: TechRep, mro: MroLocation) -> bool:
    """The rep is on the team that covers the MRO, so is kept closest to home."""
    return bool(mro.covering_base) and (
        rep.home_base.strip().lower() == mro.covering_base.strip().lower()
    )


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def _pct(rate: Decimal) -> int:
    return round(float(rate) * 100)


def _hundredths(hours: float) -> int:
    return round(hours * HOUR)


def _pay_period(day: date, periods: list[PayPeriod]) -> tuple[date, date]:
    for p in periods:
        if p.start_date <= day < p.end_date:
            return p.start_date, p.end_date
    # 24 pay periods a year (15-1.01): default to semi-monthly.
    if day.day <= 15:
        return day.replace(day=1), day.replace(day=16)
    next_month = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return day.replace(day=16), next_month


def _averaging_period(rules: CbaRules, rep: TechRep, day: date) -> tuple[date, date]:
    major = {b.strip().lower() for b in rules.major_bases}
    if rep.cba_group == 1 and rep.home_base.strip().lower() in major:
        weeks = rules.averaging_weeks_major_base
    else:
        weeks = rules.averaging_weeks_other_base
    length = timedelta(weeks=weeks)
    anchor = rules.averaging_anchor_date or rules.effective_from
    start = anchor + ((day - anchor) // length) * length
    return start, start + length


def seniority_key(rep: TechRep) -> tuple[bool, int, int]:
    """Sort key, most senior first: lower employee ID is more senior.

    A set seniority_rank (e.g. for a rehire) overrides the ID; ranked reps sort first.
    """
    return (
        rep.seniority_rank is None,
        rep.seniority_rank or 0,
        rep.id,
    )


def run(db: Session, req: ScheduleRunRequest) -> ScheduleRunResponse:
    rules = active_rules(db, req.start_time.date())
    if rules is None:
        raise NoActiveRulesError(f"No CBA rules in effect on {req.start_time.date()}")

    rest = timedelta(hours=float(rules.min_rest_hours))
    field_rest = timedelta(hours=float(max(rules.min_rest_hours, rules.post_field_rest_hours)))
    max_duty = timedelta(hours=float(rules.max_field_duty_hours))
    max_consecutive = rules.max_consecutive_worked_days
    off_window = rules.three_days_off_window_days
    off_run = rules.consecutive_days_off_required
    tier = _hundredths(float(rules.ot_voluntary_tier_hours))
    ot_rate = _pct(rules.ot_rate_voluntary)
    ot_over_rate = _pct(rules.ot_rate_voluntary_over_tier)
    mandatory_rate = _pct(rules.ot_rate_mandatory)
    field_rate = _pct(rules.field_service_rate)
    holiday_rate = _pct(rules.stat_holiday_rate)
    aog_buffer = float(rules.aog_pay_buffer_hours)
    # Far enough either side to see every rolling day window that touches the run.
    pad = timedelta(days=max(max_consecutive, off_window) + 2)
    lo, hi = req.start_time - pad, req.end_time + pad
    warnings: list[str] = []

    demand_stmt = select(MroDemand).where(
        MroDemand.status == "open",
        MroDemand.end_time > req.start_time,
        MroDemand.start_time < req.end_time,
    )
    if req.mro_id is not None:
        demand_stmt = demand_stmt.where(MroDemand.mro_id == req.mro_id)
    demands = list(db.scalars(demand_stmt.order_by(MroDemand.priority, MroDemand.start_time)))

    reps = list(
        db.scalars(
            select(TechRep)
            .where(TechRep.active)
            .options(selectinload(TechRep.certifications), selectinload(TechRep.shift_pattern))
        )
    )
    reps_by_id = {r.id: r for r in reps}
    mros = {m.id: m for m in db.scalars(select(MroLocation))}
    pay_periods = list(db.scalars(select(PayPeriod)))
    travel = {
        (t.home_base.strip().lower(), t.mro_id): float(t.travel_hours)
        for t in db.scalars(select(TravelTime))
    }
    responses: dict[int, dict[int, str]] = defaultdict(dict)
    for resp in db.scalars(
        select(DemandResponse).where(DemandResponse.demand_id.in_([d.id for d in demands]))
    ):
        responses[resp.demand_id][resp.rep_id] = resp.response

    # Load history back to the earliest averaging or pay period start for running totals.
    history_start = min(
        [_averaging_period(rules, r, req.start_time.date())[0] for r in reps]
        + [_pay_period(lo.date(), pay_periods)[0], lo.date()]
    )
    existing = list(
        db.scalars(
            select(Assignment).where(
                Assignment.status != "cancelled",
                Assignment.end_time > datetime.combine(history_start, datetime.min.time(), UTC),
                Assignment.start_time < hi,
            )
        )
    )
    unavailable = list(
        db.scalars(
            select(RepUnavailability).where(
                RepUnavailability.status == "approved",
                RepUnavailability.end_time > lo,
                RepUnavailability.start_time < hi,
            )
        )
    )
    # Approved training blocks the rep; most already have a leave row from approval.
    unavailable.extend(
        RepUnavailability(
            rep_id=t.rep_id,
            reason="training",
            start_time=t.scheduled_start,
            end_time=t.scheduled_end,
            status="approved",
        )
        for t in db.scalars(
            select(RepTraining).where(
                RepTraining.status == "approved",
                RepTraining.unavailability_id.is_(None),
                RepTraining.scheduled_end > lo,
                RepTraining.scheduled_start < hi,
            )
        )
    )
    vacation_requests = [
        u
        for u in db.scalars(
            select(RepUnavailability).where(
                RepUnavailability.reason == "vacation",
                RepUnavailability.status == "requested",
                RepUnavailability.end_time > req.start_time,
                RepUnavailability.start_time < req.end_time,
            )
        )
        if u.rep_id in reps_by_id
    ]
    holidays = set(
        db.scalars(
            select(StatutoryHoliday.holiday_date).where(
                StatutoryHoliday.holiday_date.between(lo.date(), hi.date())
            )
        )
    )

    # Running totals in hundredths: voluntary OT per pay period, regular hours per
    # averaging period.
    existing_ot: Counter[tuple[int, tuple[date, date]]] = Counter()
    existing_regular: Counter[tuple[int, tuple[date, date]]] = Counter()
    busy_by_rep: dict[int, list[tuple[datetime, datetime, bool]]] = defaultdict(list)
    worked_by_rep: dict[int, set[date]] = defaultdict(set)
    for a in existing:
        rep = reps_by_id.get(a.rep_id)
        if rep is None:
            continue
        tz = _tz(mros[a.mro_id].timezone)
        day = a.start_time.astimezone(tz).date()
        if a.overtime_type == "voluntary":
            existing_ot[rep.id, _pay_period(day, pay_periods)] += _hundredths(
                float(a.overtime_hours)
            )
        hours = (a.end_time - a.start_time).total_seconds() / 3600
        existing_regular[rep.id, _averaging_period(rules, rep, day)] += _hundredths(
            max(0.0, hours - float(a.overtime_hours))
        )
        if a.end_time > lo:
            travel_td = timedelta(hours=float(a.travel_hours))
            start, end = a.start_time - travel_td, a.end_time + travel_td
            busy_by_rep[rep.id].append((start, end, _is_field_service(rep, mros[a.mro_id])))
            worked_by_rep[rep.id].update(_hours_by_local_date(start, end, tz))

    unavailable_by_rep: dict[int, list[RepUnavailability]] = defaultdict(list)
    for u in unavailable:
        unavailable_by_rep[u.rep_id].append(u)
    already_filled = Counter(a.demand_id for a in existing if a.demand_id is not None)
    already_on = {(a.rep_id, a.demand_id) for a in existing if a.demand_id is not None}

    # 19-1.01 to 19-1.03: a pattern's scheduled hours must fit the weekly average.
    for pattern in {r.shift_pattern for r in reps if r.shift_pattern is not None}:
        weekly = float(pattern.shift_hours) * pattern.cycle.count("W") * 7 / len(pattern.cycle)
        if weekly > float(rules.avg_weekly_hours) + 0.05:
            warnings.append(
                f"Shift pattern {pattern.code} schedules {weekly:.2f} h/week, over the "
                f"{float(rules.avg_weekly_hours):g} h average"
            )

    demand_days = {
        d.id: _hours_by_local_date(d.start_time, d.end_time, _tz(mros[d.mro_id].timezone))
        for d in demands
    }

    model = cp_model.CpModel()
    x: dict[tuple[int, int], cp_model.IntVar] = {}
    pairs: dict[tuple[int, int], _Pair] = {}
    seniority_rank: dict[tuple[int, int], int] = {}
    remaining: dict[int, int] = {}
    reasons: dict[int, str] = {}
    blocked: dict[int, Counter[str]] = defaultdict(Counter)
    missing_travel: set[tuple[str, str]] = set()

    for d in demands:
        remaining[d.id] = d.reps_needed - already_filled[d.id]
        if remaining[d.id] <= 0:
            continue
        if d.end_time - d.start_time > max_duty:
            reasons[d.id] = (
                f"Longer than the {float(rules.max_field_duty_hours):g} h max duty day; "
                "split it into one demand per shift"
            )
            continue
        certified = [r for r in reps if _is_certified(r, d)]
        if not certified:
            reasons[d.id] = "No active rep holds a valid certification for this aircraft type"
            continue

        mro = mros[d.mro_id]
        tz = _tz(mro.timezone)
        solicited = responses.get(d.id, {})
        mandatory_here: list[TechRep] = []
        for rep in certified:
            if (rep.id, d.id) in already_on:
                continue
            field = _is_field_service(rep, mro)
            travel_hours = 0.0
            if field:
                known = travel.get((rep.home_base.strip().lower(), mro.id))
                if known is None:
                    missing_travel.add((rep.home_base, mro.facility_name))
                else:
                    travel_hours = known
            travel_td = timedelta(hours=travel_hours)
            # 21-1.03: travel to the site counts toward the duty day.
            if d.end_time - d.start_time + travel_td > max_duty:
                blocked[d.id]["duty"] += 1
                continue
            busy_start, busy_end = d.start_time - travel_td, d.end_time + travel_td
            if any(
                _overlaps(u.start_time, u.end_time, busy_start, busy_end)
                for u in unavailable_by_rep[rep.id]
            ):
                blocked[d.id]["unavailable"] += 1
                continue
            if any(
                _overlaps(s - gap, e + gap, busy_start, busy_end)
                for s, e, f in busy_by_rep[rep.id]
                for gap in [field_rest if field or f else rest]
            ):
                blocked[d.id]["booked"] += 1
                continue

            overtime = flexible = holiday_regular = 0.0
            for day, hours in demand_days[d.id].items():
                work_day = _is_pattern_work_day(rep, day)
                if work_day is None:
                    flexible += hours
                    regular = hours
                elif work_day:
                    regular = min(hours, float(rep.shift_pattern.shift_hours))
                    overtime += hours - regular
                else:
                    regular = 0.0
                    overtime += hours
                if day in holidays:
                    holiday_regular += regular

            # Solicited demands: reps who did not accept can only be assigned mandatorily.
            needs_consent = field or overtime > 0 or flexible > 0
            mandatory = bool(solicited) and solicited.get(rep.id) != "accepted" and needs_consent
            if mandatory and not req.allow_mandatory:
                blocked[d.id]["declined"] += 1
                continue

            paid = sum(demand_days[d.id].values())
            if field:
                paid += 2 * travel_hours
                if d.demand_type == "aog":
                    # 21-3.02: paid from 2 h before the start until 2 h after getting home.
                    paid += 2 * aog_buffer

            # No duplication of premiums for the same hours (16-1.05).
            if mandatory and field:
                # 21-2.12: all hours including travel at the mandatory rate.
                cost = (mandatory_rate - 100) * _hundredths(paid)
                flex_rate = 0
            elif mandatory:
                cost = (mandatory_rate - 100) * _hundredths(overtime) + (
                    holiday_rate - 100
                ) * _hundredths(holiday_regular)
                flex_rate = mandatory_rate - 100
            elif field:
                # 21-2.02, 21-3.02: all hours including travel at the field service rate.
                cost = (max(field_rate, holiday_rate) - 100) * _hundredths(paid)
                flex_rate = 0
            else:
                cost = (ot_rate - 100) * _hundredths(overtime) + (holiday_rate - 100) * _hundredths(
                    holiday_regular
                )
                flex_rate = ot_rate - 100

            day0 = d.start_time.astimezone(tz).date()
            x[rep.id, d.id] = model.new_bool_var(f"x_{rep.id}_{d.id}")
            pairs[rep.id, d.id] = _Pair(
                field_service=field,
                home_team=is_home_team(rep, mro),
                mandatory=mandatory,
                travel_hours=travel_hours,
                paid_hours=round(paid, 2),
                overtime_hours=round(overtime, 2),
                flexible_hours=round(flexible, 2),
                flex_ot_rate=flex_rate,
                fixed_cost=cost,
                busy_start=busy_start,
                busy_end=busy_end,
                pay_period=_pay_period(day0, pay_periods),
                averaging_period=_averaging_period(rules, rep, day0),
            )
            if mandatory:
                mandatory_here.append(rep)

        # 16-1.06, 21-2.09, 21-3.08: mandatory work goes in reverse seniority.
        junior_first = sorted(mandatory_here, key=seniority_key, reverse=True)
        for rank, rep in enumerate(junior_first):
            seniority_rank[rep.id, d.id] = min(rank, MAX_SENIORITY_RANK)

        demand_vars = [v for (_, q), v in x.items() if q == d.id]
        if demand_vars:
            model.add(sum(demand_vars) <= remaining[d.id])

    for home, facility in sorted(missing_travel):
        warnings.append(f"No travel time from {home} to {facility}; assumed 0 h")

    # Weekly cap on reps on vacation, counting approved leave and granted requests.
    mro_list = list(mros.values())
    cap = rules.max_reps_off_per_week

    def weeks_of(u: RepUnavailability) -> set[date]:
        tz = home_tz(reps_by_id[u.rep_id], mro_list)
        days = _hours_by_local_date(u.start_time, u.end_time, tz)
        return {d - timedelta(days=d.weekday()) for d in days}

    approved_off: dict[date, set[int]] = defaultdict(set)
    for u in unavailable:
        if u.reason == "vacation" and u.rep_id in reps_by_id:
            for week in weeks_of(u):
                approved_off[week].add(u.rep_id)
    first_week = req.start_time.date() - timedelta(days=6)
    for week, off in sorted(approved_off.items()):
        if len(off) > cap and first_week <= week < req.end_time.date():
            warnings.append(
                f"Week of {week}: {len(off)} reps already on approved vacation, "
                f"over the limit of {cap}"
            )

    grant: dict[int, cp_model.IntVar] = {}
    requesters = sorted({reps_by_id[u.rep_id] for u in vacation_requests}, key=seniority_key)
    vacation_rank = {r.id: min(i, MAX_SENIORITY_RANK) for i, r in enumerate(requesters)}
    requested_off: dict[date, dict[int, list[cp_model.IntVar]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for u in vacation_requests:
        if any(_overlaps(s, e, u.start_time, u.end_time) for s, e, _ in busy_by_rep[u.rep_id]):
            warnings.append(f"Vacation request {u.id} overlaps existing assignments")
            continue
        grant[u.id] = g = model.new_bool_var(f"vac_{u.id}")
        for week in weeks_of(u):
            if u.rep_id not in approved_off[week]:
                requested_off[week][u.rep_id].append(g)
        for (r, q), v in x.items():
            p = pairs[r, q]
            if r == u.rep_id and _overlaps(p.busy_start, p.busy_end, u.start_time, u.end_time):
                model.add(g + v <= 1)
    for week, by_rep in requested_off.items():
        off_vars: list[cp_model.IntVar] = []
        for rep_id, grants in by_rep.items():
            if len(grants) == 1:
                off_vars.append(grants[0])
            else:
                off = model.new_bool_var(f"vac_week_{rep_id}_{week.isoformat()}")
                model.add_max_equality(off, grants)
                off_vars.append(off)
        model.add(sum(off_vars) <= max(0, cap - len(approved_off[week])))

    # Continuity: each rep's share of recent worked days at each MRO.
    lookback = req.start_time - timedelta(days=rules.continuity_lookback_days)
    days_at: Counter[tuple[int, int]] = Counter()
    for a in db.scalars(
        select(Assignment).where(
            Assignment.status != "cancelled",
            Assignment.start_time >= lookback,
            Assignment.start_time < req.start_time,
        )
    ):
        tz = _tz(mros[a.mro_id].timezone)
        days_at[a.rep_id, a.mro_id] += len(_hours_by_local_date(a.start_time, a.end_time, tz))
    days_worked: Counter[int] = Counter()
    for (rep_id, _), n in days_at.items():
        days_worked[rep_id] += n
    continuity = {key: CONTINUITY_WEIGHT * n // days_worked[key[0]] for key, n in days_at.items()}

    demands_by_id = {d.id: d for d in demands}
    reg_vars: dict[tuple[int, int], cp_model.IntVar] = {}
    tier_costs: list[cp_model.LinearExprT] = []
    for rep in reps:
        candidates = sorted(
            (demands_by_id[q] for (r, q) in x if r == rep.id),
            key=lambda d: pairs[rep.id, d.id].busy_start,
        )
        if not candidates:
            continue

        # Two demands for the same rep must not overlap and must leave the minimum rest.
        for i, d1 in enumerate(candidates):
            p1 = pairs[rep.id, d1.id]
            for d2 in candidates[i + 1 :]:
                p2 = pairs[rep.id, d2.id]
                gap = field_rest if p1.field_service or p2.field_service else rest
                if p2.busy_start < p1.busy_end + gap:
                    model.add_at_most_one([x[rep.id, d1.id], x[rep.id, d2.id]])

        # 19-1.01 to 19-1.03: reps without a pattern keep regular hours within the average.
        regs_by_period: dict[tuple[date, date], list[cp_model.IntVar]] = defaultdict(list)
        for d in candidates:
            p = pairs[rep.id, d.id]
            if p.flexible_hours > 0:
                flex = _hundredths(p.flexible_hours)
                reg = model.new_int_var(0, flex, f"reg_{rep.id}_{d.id}")
                model.add(reg <= flex * x[rep.id, d.id])
                reg_vars[rep.id, d.id] = reg
                regs_by_period[p.averaging_period].append(reg)
        for period, regs in regs_by_period.items():
            cap = _hundredths(float(rules.avg_weekly_hours) * (period[1] - period[0]).days / 7)
            model.add(sum(regs) <= max(0, cap - existing_regular[rep.id, period]))

        # 16-1.04: voluntary overtime past the tier in a pay period is paid at the higher rate.
        ot_by_period: dict[tuple[date, date], list[cp_model.LinearExprT]] = defaultdict(list)
        ot_bound: Counter[tuple[date, date]] = Counter()
        for d in candidates:
            p = pairs[rep.id, d.id]
            if p.mandatory or (p.overtime_hours == 0 and p.flexible_hours == 0):
                continue
            expr = _hundredths(p.overtime_hours) * x[rep.id, d.id]
            if (rep.id, d.id) in reg_vars:
                expr += _hundredths(p.flexible_hours) * x[rep.id, d.id] - reg_vars[rep.id, d.id]
            ot_by_period[p.pay_period].append(expr)
            ot_bound[p.pay_period] += _hundredths(p.overtime_hours + p.flexible_hours)
        for period, exprs in ot_by_period.items():
            already = existing_ot[rep.id, period]
            over = model.new_int_var(0, already + ot_bound[period], f"over_{rep.id}_{period[0]}")
            model.add(over >= already + sum(exprs) - tier)
            tier_costs.append((ot_over_rate - ot_rate) * over)

        # Max consecutive worked days, counting pattern work days and existing assignments.
        day_vars: dict[date, list[cp_model.IntVar]] = defaultdict(list)
        for d in candidates:
            p = pairs[rep.id, d.id]
            tz = _tz(mros[d.mro_id].timezone)
            for day in _hours_by_local_date(p.busy_start, p.busy_end, tz):
                day_vars[day].append(x[rep.id, d.id])

        off_days: set[date] = set()
        for u in unavailable_by_rep[rep.id]:
            off_days.update(_hours_by_local_date(u.start_time, u.end_time, UTC))

        span = max(max_consecutive, off_window - 1)
        first = min(day_vars) - timedelta(days=span)
        last = max(day_vars) + timedelta(days=span)
        days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
        worked_on: list[int | cp_model.IntVar] = []
        for day in days:
            if day in worked_by_rep[rep.id] or (
                _is_pattern_work_day(rep, day) and day not in off_days
            ):
                worked_on.append(1)
            elif day in day_vars:
                w = model.new_bool_var(f"w_{rep.id}_{day.isoformat()}")
                model.add_max_equality(w, day_vars[day])
                worked_on.append(w)
            else:
                worked_on.append(0)

        window = max_consecutive + 1
        for i in range(len(days) - window + 1):
            segment = worked_on[i : i + window]
            if any(not isinstance(v, int) for v in segment):
                model.add(sum(segment) <= max_consecutive)

        # 19-1.07: a run of consecutive days off in every rolling window.
        if rep.shift_pattern is not None and rep.shift_pattern.requires_consecutive_days_off:
            # None marks a run that is off whatever the solver picks.
            runs: dict[int, cp_model.IntVar | None] = {}
            for s in range(len(days) - off_run + 1):
                segment = worked_on[s : s + off_run]
                if any(isinstance(v, int) and v == 1 for v in segment):
                    continue
                choices = [v for v in segment if not isinstance(v, int)]
                if not choices:
                    runs[s] = None
                    continue
                run_off = model.new_bool_var(f"off_{rep.id}_{s}")
                for v in choices:
                    model.add(run_off + v <= 1)
                runs[s] = run_off
            for i in range(len(days) - off_window + 1):
                if all(isinstance(v, int) for v in worked_on[i : i + off_window]):
                    continue
                inside = [runs[s] for s in range(i, i + off_window - off_run + 1) if s in runs]
                # An empty list means the existing schedule already breaks the rule.
                if inside and all(r is not None for r in inside):
                    model.add(sum(inside) >= 1)

    objective: list[cp_model.LinearExprT] = []
    for (r, q), v in x.items():
        p = pairs[r, q]
        value = (
            PRIORITY_WEIGHT * (6 - demands_by_id[q].priority)
            + continuity.get((r, demands_by_id[q].mro_id), 0)
            + (HOME_TEAM_WEIGHT if p.home_team else 0)
            - p.fixed_cost
            - (p.flex_ot_rate + 1) * _hundredths(p.flexible_hours)
        )
        if p.mandatory:
            value -= MANDATORY_PENALTY + SENIORITY_STEP * seniority_rank[r, q]
        objective.append(value * v)
    for u in vacation_requests:
        if u.id in grant:
            weight = VACATION_WEIGHT - SENIORITY_STEP * vacation_rank[u.rep_id]
            objective.append(weight * grant[u.id])
    # The +1 keeps hours regular when the overtime rate would cost nothing extra.
    for (r, q), reg in reg_vars.items():
        objective.append((pairs[r, q].flex_ot_rate + 1) * reg)
    objective.extend(-cost for cost in tier_costs)
    model.maximize(sum(objective))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = settings.solver_max_seconds
    result = solver.solve(model)
    solved = result in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    chosen = [(r, q) for (r, q), v in x.items() if solved and solver.value(v)]
    proposals: list[ProposedAssignment] = []
    for r, q in chosen:
        p = pairs[r, q]
        flex_ot = p.flexible_hours
        if (r, q) in reg_vars:
            flex_ot -= solver.value(reg_vars[r, q]) / HOUR
        cost = p.fixed_cost + p.flex_ot_rate * _hundredths(flex_ot)
        proposals.append(
            ProposedAssignment(
                demand_id=q,
                rep_id=r,
                mro_id=demands_by_id[q].mro_id,
                start_time=demands_by_id[q].start_time,
                end_time=demands_by_id[q].end_time,
                field_service=p.field_service,
                mandatory=p.mandatory,
                travel_hours=p.travel_hours,
                paid_hours=p.paid_hours,
                overtime_hours=round(p.overtime_hours + flex_ot, 2),
                premium_hours=round(cost / (100 * HOUR), 2),
            )
        )

    assigned = Counter(q for _, q in chosen)
    eligible = Counter(q for _, q in x)
    unfilled: list[UnfilledDemand] = []
    for d in demands:
        still_needed = remaining[d.id] - assigned[d.id]
        if still_needed <= 0:
            continue
        if d.id in reasons:
            reason = reasons[d.id]
        elif eligible[d.id] == 0:
            reason = "No eligible rep"
            if blocked[d.id]:
                reason += ": " + "; ".join(
                    f"{n} {BLOCKED_MESSAGES[key]}" for key, n in blocked[d.id].most_common()
                )
        elif eligible[d.id] < remaining[d.id]:
            reason = f"Only {eligible[d.id]} eligible rep(s) for {remaining[d.id]} needed"
        else:
            reason = (
                "Eligible reps were used for higher-priority demands "
                "or would break a rest, consecutive-day, days-off, or hours limit"
            )
        unfilled.append(UnfilledDemand(demand_id=d.id, still_needed=still_needed, reason=reason))

    granted = [
        u for u in vacation_requests if u.id in grant and solved and solver.value(grant[u.id])
    ]
    if req.save and (proposals or granted):
        for u in granted:
            u.status = "approved"
        rows = [
            Assignment(
                rep_id=p.rep_id,
                mro_id=p.mro_id,
                aircraft_type_id=demands_by_id[p.demand_id].aircraft_type_id,
                demand_id=p.demand_id,
                start_time=p.start_time,
                end_time=p.end_time,
                status="proposed",
                overtime_type=(
                    "mandatory"
                    if p.mandatory
                    else "voluntary"
                    if p.overtime_hours > 0
                    else "none"
                ),
                overtime_hours=Decimal(str(p.overtime_hours)),
                travel_hours=Decimal(str(p.travel_hours)),
            )
            for p in proposals
        ]
        db.add_all(rows)
        db.commit()
        for p, row in zip(proposals, rows, strict=True):
            p.assignment_id = row.id

    return ScheduleRunResponse(
        status=solver.status_name(result),
        cba_rules_id=rules.id,
        assignments=proposals,
        unfilled=unfilled,
        warnings=warnings,
        vacation_granted=[u.id for u in granted],
        vacation_not_granted=sorted({u.id for u in vacation_requests} - {u.id for u in granted}),
    )

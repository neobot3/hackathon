# Scheduling Rules

Rules the Tech Rep Scheduler follows, from two sources:

- **CBA:** the WestJet / AMFA collective agreement, 2024-2029 ([CBA.txt](CBA.txt)). Clause numbers are in brackets.
- **Meeting:** the scheduler meeting with Dave and Jason on October 16, 2026 ([Meeting.vtt](Meeting.vtt)).

Tech Reps (Technical Representative and Technical Representative Lead) are a Group III classification [18-4.01, 18-4.02]. CBA rules below are limited to those that apply to Group III or to scheduling in general.

The **In the App** column names where the rule is enforced. "Not enforced" means the rule is recorded here but the app does not check it yet.

---

## CBA Rules

### Seniority

| Rule | Clause | In the App |
| --- | --- | --- |
| Union Seniority is cumulative service in covered classifications. Training counts as time worked. | 13-1.01 | `tech_reps.seniority_rank`, `union_seniority_date` |
| On equal seniority dates, the lower employee number is more senior. | 13-1.03 | `seniority_key()` in `services/scheduler.py` |
| The Master Seniority List is published every February 1 and August 1. | 13-2.01 | Not enforced |
| Seniority is forfeited on leaving the company, layoff over 3 years, or more than 24 months in a non-union role, among others. A rehired employee keeps the employee number but not the seniority. | 13-4.01 | Set `seniority_rank` by hand on rehire |

### Hours of Service and Shift Pattern

| Rule | Clause | In the App |
| --- | --- | --- |
| Group III works a 7-on/7-off pattern. | 19-1.10, 19-2.04 | `shift_patterns` row `7-7` |
| 7-7 shifts are 11.42 hours, including two paid 30-minute meal periods. | 19-1.10 | `shift_patterns.shift_hours` |
| Group III averages 40 hours a week over a 52-week period. | 19-1.03 | Solver averaging constraint |
| A work week runs Monday to Sunday. | 19-1.04 | Vacation weeks start on Monday |
| Schedule at most 7 consecutive days. | 19-1.05 | `max_consecutive_scheduled_days`; `shift_pattern` alert |
| Work at most 11 consecutive days. | 19-1.06 | `max_consecutive_worked_days`; `rest` alert |
| 5-5-4 pattern: at least 48 hours off in each set of days off, as two 24-hour periods that need not be consecutive. At least one run of 3 consecutive days off in any 28 days. | 19-1.07 | `min_hours_off_per_set`; `rest` alert (applied to every pattern, see the meeting) |
| 7-7 day shifts start between 0500 and 0800 local, afternoons 1300-1500, nights 1800-2100. | 19-5.01 | `shift_start_windows` |
| At least 10 hours rest between scheduled shifts. Trades and pick-ups may cut this to 8. | 19-7.01, 19-7.02 | `min_rest_hours`, `min_rest_hours_trade`; `rest` alert |
| A bid schedule is posted at least 30 days before it takes effect. | 19-2.06 | Not enforced |
| An awarded or assigned schedule is posted at least 15 days before it takes effect. | 19-2.07 | `schedule_horizon` alert uses the stricter 30-day meeting rule |
| Shift trades need manager approval and cannot be used to get overtime. | 19-8.01, 19-8.03 | Not enforced |

### Overtime and Time Bank

| Rule | Clause | In the App |
| --- | --- | --- |
| A manager authorizes all overtime in advance. | 16-1.01 | Manual |
| Overtime and open shifts on a day off pay 1.5x. | 16-1.02 | `ot_rate_voluntary` |
| The first 8 overtime hours in a pay period pay 1.5x. Hours beyond 8 pay 1.75x. | 16-1.04 | `ot_voluntary_tier_hours`, `ot_rate_voluntary_over_tier` |
| No double premiums for the same hours. | 16-1.05 | Solver cost model |
| Mandatory overtime pays 2x and goes in reverse seniority order. | 16-1.06 | `ot_rate_mandatory`; solver and `seniority` alert |
| Open shifts at a base go first come, first served to qualified employees there. The employee must still meet rest and consecutive-day limits. | 16-2.03, 16-2.04 | Overtime opportunities list |
| Employees can bank overtime. Banked hours convert at the overtime rate they were earned at. | 15-4.01 | `tech_reps.banked_ot_hours` |
| At most 80 banked hours. Hours over the limit are paid out. | 15-4.02 | `max_banked_ot_hours` |
| A time-bank payout is at the regular rate. | 15-4.03 | Not enforced |
| Salary is paid over 24 pay periods a year. | 15-1.01 | `pay_periods` |

### Field Service, Base Coverage and AOG

| Rule | Clause | In the App |
| --- | --- | --- |
| Field Service is any temporary assignment away from base: planned (Base Coverage) or unplanned (AOG). | 21-1.01 | Field service when the MRO is not the rep's home base |
| Qualified employees at a staffed base get first consideration for field service there. | 21-1.02 | Overtime list shows the covering team first |
| Duty day of at most 16 hours per 24 hours of field service, travel included. | 21-1.03 | `max_field_duty_hours`; solver |
| If the trip home would pass 16 duty hours, the employee may rest 10 hours on site first. | 21-1.04 | `post_field_rest_hours` |
| An employee back from multi-day field service may skip a shift on the same day, unpaid. | 21-1.06 | Not enforced |
| Company vehicle travel is limited to a 550 km radius. | 21-1.09 | `max_vehicle_travel_km` |
| Base Coverage needs at least 48 hours notice. | 21-2.01 | `base_coverage_notice_hours` |
| Voluntary Base Coverage pays 1.5x for all hours, travel included. | 21-2.02 | `field_service_rate` |
| Base Coverage lists are regional (Western, Central, Eastern) and reset by seniority every December 31. The top qualified employee gets the assignment and moves to the bottom. | 21-2.03 to 21-2.07 | Not enforced; the app ranks by seniority |
| If no one accepts, Base Coverage is assigned in reverse seniority and pays 2x. A rep assigned this way is not assigned again until everyone else in the region has been. | 21-2.09, 21-2.11, 21-2.12 | Solver mandatory assignment |
| AOG pays 1.5x from 2 hours before the start until 2 hours after getting home. Mandatory AOG pays 2x. | 21-3.02, 21-3.11 | `aog_pay_buffer_hours` |
| AOG lists are per base, reset by seniority every December 31. Mandatory AOG goes in reverse seniority. | 21-3.04 to 21-3.08 | Not enforced; solver uses reverse seniority |

### Vacation and Statutory Holidays

| Rule | Clause | In the App |
| --- | --- | --- |
| The vacation year runs January 1 to December 31. Vacation does not carry over. | 29-1.03, 29-1.04 | `vacation_unused` alert |
| Vacation blocks are bid in seniority order. | 29-1.05, 29-5.01 | Vacation award |
| The company cannot change awarded vacation without written agreement, or make an employee work during it. | 29-1.08, 29-1.12 | Vacation is approved leave; assignments over it raise `vacation_limit` |
| Change requests are accepted only after all bids are complete. The employee gets an answer within 5 days. | 29-1.10 | Not enforced |
| Allotment: 80 hours in years 1-3, 120 from year 4, 160 from year 7, 200 from year 25. | 29-2.02 | `leave_balances` (entered by hand) |
| 11 statutory holidays: the 10 Canada Labour Code holidays plus Civic Holiday. | 29-3.01 | `statutory_holidays` |
| Group III bids the 11 stat holidays with vacation, as 11 Vacation Bid Allotment Days. | 29-3.03 to 29-3.05 | Award uses vacation plus stat balance |
| Stat time off counts as taken after all vacation for the year. | 29-3.05 | Leave recount charges vacation first, then stat |
| At least one vacation block per 5.5 employees in the same base, classification and crew. | 29-4.01 | `max_reps_off_per_week` (set to 3 from the meeting) |
| Allotment lists post on October 15. | 29-4.04 | Not enforced |
| Three bid rounds. Rounds 1 and 2: up to 2 full blocks each. Round 3: remaining days, full or partial blocks. | 29-4.06 to 29-4.12 | Not enforced; bids are whole weeks |
| Round 3 awards all full-block bids by seniority before any partial-block bids. | 29-5.02 | Not enforced |
| Employees who do not bid have their vacation assigned by the company. | 29-4.13 | Manual |
| Time left at year end can be picked from open blocks in the first quarter of the next year. | 29-7.04 | Not enforced |

### Sick Leave

| Rule | Clause | In the App |
| --- | --- | --- |
| Report sick at least 2 hours before the shift. | 30-1.02 | Not enforced |
| A doctor's note can be required after 5 or more consecutive sick days. | 30-1.03 | Not enforced |
| 12 paid sick days credited each January 1. | 30-2.01 | `leave_balances` (sick) |
| Prorated by month for employees hired during the year: Jan 12, Feb 11, Mar 10, Apr 9, May 9, Jun 7, Jul 7, Aug 6, Sep 4, Oct 4, Nov 3, Dec 3. | 30-2.02 | `sick_leave_allowance` (see Where the Sources Differ) |
| Sick days do not carry over. | 30-2.03 | Yearly balance |
| Sick leave is used in full days. A shift spanning two calendar days uses one day. | 30-2.06 | Leave counted per work day |
| Once paid sick days run out, more sick time is unpaid. Paid days must be used first. | 30-2.07 | `sick_limit` alert |
| 3 paid and 2 unpaid personal days, separate from sick leave. | 30-3.01 | Not enforced |

### Training

| Rule | Clause | In the App |
| --- | --- | --- |
| Training and travel to and from training count as hours worked. | 34-1.01 | Approved training blocks the rep |
| Training of 8 hours or more is a full shift. On a day off, only the training hours pay overtime. | 34-1.02 | Not enforced |
| Training or training travel outside the shift or on a day off pays overtime. | 34-1.04, 34-1.05 | Not enforced |
| At least 14 days notice of in-person training. On request, training moves into the regular shift unless that would let a qualification lapse. | 34-1.06 | Not enforced |
| Out-of-base training includes hotel, transport and meal cost replacement. | 34-1.07, 42-1.01 | Not enforced |
| Extended Training (aircraft type courses) can change the shift pattern with 14 days notice. The employee gets 36 hours of paid rest before and after. | 34-3.01 | Not enforced |
| Extended Training seats go by seniority from an eligibility list. Completing it moves the employee to the bottom. Extended Training wins over a clashing recurrent course, which is rescheduled. | 34-3.02 | Not enforced |

---

## Meeting Rules

### Schedule Building

| Rule | In the App |
| --- | --- |
| Build each rep's schedule at least 30 days ahead. In mid-October, November is fully plotted. | `schedule_publish_days` (30); `schedule_horizon` alert |
| The Heavy Maintenance Schedule drives where reps go. Dave often hears about changes before the schedule is updated. | Maintenance events create demands |
| Reps work 7-on/7-off rotations at the MROs. | `7-7` pattern |
| The goal is a full-year schedule built from awarded vacation, qualifications, home base, sick time and training. | Schedule runs |

### Days Off and Rest

| Rule | In the App |
| --- | --- |
| Each set of days off needs at least 48 hours off. The free days need not be consecutive. Example: training on the 2nd to 4th, off the 5th, work the 6th to 9th, off the 10th, overtime on the 11th. | `rest` alert in `_check_days_off()` |
| After a run of work or overtime, a rep rests 2 days before more overtime. | `min_days_off_between_rotations` (2) |

### Training

| Rule | In the App |
| --- | --- |
| Training is mostly scheduled on days off, as overtime. | Overtime pay for training not modeled |
| On shift, training must fall on the first or last day of the rotation. In the middle, the rep would have to leave the MRO and fly back. Dave rejects mid-rotation dates. | `training_conflict` alert in `_check_training_in_rotation()` |
| Training runs in Calgary, or in Toronto for eastern-based reps. | `location` on the training due list |
| Recurrent training (HF, CRM, Hot Topics) is 3 consecutive days, every 2 years. It is needed to hold a WestJet ACA. | Training type, 24-month recurrence |
| First Aid and Fire Extinguisher training are every 3 years. Nothing is yearly. | Training types, 36-month recurrence |
| Endorsement courses take 4 to 5 weeks in Calgary. On completion, the aircraft type is added to the rep's endorsements. | Training types with `aircraft_type_id`; certification added on completion |
| Endorsements are NG, MAX, BCF, Q400 and 787. | `aircraft_types` |
| The training department submits dates. The scheduler accepts or rejects them. A rejection goes back with a note. | Training dashboard, Pending approval; reject `note` |

### Home Base and Coverage

| Rule | In the App |
| --- | --- |
| The Kelowna team covers Kelowna. | `covering_base` `YLW` |
| The Toronto team covers the east: JD Aero, AAR in Windsor, and FlightStar in Florida. | `covering_base` `YYZ` |
| The Calgary team covers the rest, such as Tucson and San Antonio. Calgary has no MRO, so its reps always travel. | `covering_base` `YYC` |
| Calgary also backs up the east and covers Kelowna vacation. | Other teams stay eligible |
| Keep reps as close to home as possible. | Solver home-team weight; travel cost |
| Keep a rep at the same MRO for 2 to 3 rotations instead of moving every week. | Solver continuity weight |

### Overtime

| Rule | In the App |
| --- | --- |
| Overtime goes by seniority, not employee number. A rehired rep keeps the old employee number but loses seniority. | `seniority_rank`; `seniority` alert |
| Offer overtime to all reps on days off at the base that covers the work. Award it to the most senior rep who says yes. | Overtime list: covering team first, then by seniority |
| The scheduler cannot hand-pick a rep for overtime based on experience with an aircraft type. | Seniority order |
| Overtime can be paid out or banked. Banked time can be used as vacation. | `banked_ot_hours` |

### Vacation and Stat Holidays

| Rule | In the App |
| --- | --- |
| Coordinators post each rep's vacation allotment, in seniority order. | `leave_balances` |
| Bidding has 3 rounds. Rounds 1 and 2 accept only full 7-day blocks. | Bids are whole weeks |
| At most 3 reps on vacation at once. Clashes go to the most senior. | `max_reps_off_per_week` (3); award by seniority |
| Round 3 usually has a few days left over. Reps fill the rest of the rotation with banked time. | Not enforced |
| Next year's vacation must be entered by the end of November. If a rep does not bid, the manager picks the vacation. | `vacation_unused` alert from December 1 |
| After January 1, a rep may move vacation only to a rotation with fewer than 3 people off. | Weekly cap |
| All vacation must be used by December 31 or it is lost. WestJet has sometimes allowed it in the first quarter. | `vacation_unused` alert |
| Reps get their 11 stat holidays up front and bid them with vacation. They do not get the stat day off automatically. | Vacation plus stat balance |
| A rep may take a stat day in lieu, for example to avoid spending it away from home. | Not enforced |
| Taking 7 vacation days gives 21 days off, because of the 7 days off on each side. | Weekly bids on the 7-7 pattern |

### Sick Leave

| Rule | In the App |
| --- | --- |
| 12 paid sick days a year, prorated by month: 12 in January, 11 in February, 10 in March and so on. | `sick_leave_allowance`; `sick_limit` alert |
| Once paid sick days run out, sick time is unpaid. | `sick_limit` alert |
| Sick before travel makes the first rotation day a sick day. Sick on site is a sick day at the MRO. | Approved sick leave |
| A rep back from sick leave does not make up the missed days. | No makeup logic |

### Travel

| Rule | In the App |
| --- | --- |
| A rep travels on day 1 of the rotation, works days 2 to 6, and travels home on day 7. | Travel hours per MRO |
| A rep may take a travel day on overtime before the rotation. | Manual assignment |
| Travel days pay a full 12-hour shift, because travel over 4 hours counts as a full shift. Dave was not sure of the CBA clause. | Not enforced |
| Kelowna is a 45-minute flight. A rep flies in that morning and works the same day. | `travel_times` |

### Maintenance Volatility

| Rule | In the App |
| --- | --- |
| Avoid days with no rep at an active MRO between one rep leaving and the next arriving, especially around deliveries. | `coverage_gap` alert per support day |
| Unplanned events: AOG, lease returns, bird strikes, hard landings, hail damage, MRO starts and finishes, and last-minute sales or delivery requests. | Maintenance event types and demands |
| Warn before scheduling a rep at an MRO after its last aircraft of that type returns to service. | `no_aircraft` alert |
| Reps want to know where they are going as far ahead as possible. | `schedule_horizon` alert |

---

## Where the Sources Differ

| Topic | CBA | Meeting | App Follows |
| --- | --- | --- | --- |
| 48 hours off per set of days off | Written for the 5-5-4 pattern [19-1.07] | Applied to tech reps on 7-7 | Meeting: all patterns |
| How far ahead the schedule is posted | 15 days for awarded schedules [19-2.07] | 30 days | Meeting: 30 days |
| Sick day proration | Table for employees hired mid-year: May 9, Jun 7, Sep 4, Dec 3 [30-2.02] | Straight line, 1 fewer per month | Seed values: May 8, Jun 8, Sep 5, Dec 2. Check against the CBA table. |
| Who is asked first for coverage | Regional Base Coverage lists (Western, Central, Eastern), rotated [21-2.03] | Team at the covering home base, then seniority | Meeting |
| Travel day pay | Base Coverage pays 1.5x for travel time [21-2.02] | Full 12-hour shift when travel is over 4 hours | CBA |
| Shift length | 11.42 hours on 7-7 [19-1.10] | 12-hour shift | CBA |

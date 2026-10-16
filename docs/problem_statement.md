# Problem statement: MRO Tech Rep scheduling

## Official challenge statement

> How can we automate Tech Rep scheduling based on MRO location, aircraft type, Tech Rep qualifications, availability, location, overtime considerations, and CBA work/rest rules, replacing today's manual Excel-based process?
>
> Today, this process relies heavily on manual coordination and spreadsheets. The opportunity is to explore how technology, automation, and intelligent decision-making can simplify scheduling while balancing operational requirements, workforce constraints, qualifications, and regulatory considerations.
>
> There are lots of interesting angles to explore, from optimization and automation to decision support, workforce planning, and creating a better experience for those managing the scheduling process.

## Scheduling factors

The statement names these factors. The table shows how each one maps to the current project.

| Factor | Where it lives today |
| --- | --- |
| MRO location | `mro_locations` table |
| Aircraft type | `aircraft_types` table |
| Tech Rep qualifications | `tech_rep_certifications` table, and the solver's certification check |
| Availability | Not modeled yet |
| Location (rep) | `tech_reps.home_base` |
| Overtime considerations | Not modeled yet |
| CBA work/rest rules | Not modeled yet |

## Our approach

Our team's interpretation, not part of the official statement:

- **Optimization:** Model scheduling as a constraint problem and solve it with Google OR-Tools CP-SAT. Qualifications, availability, and CBA work/rest rules are hard constraints. Overtime and travel are costs to minimize.
- **Decision support:** The solver proposes a schedule, and the scheduler reviews, accepts, or overrides it.
- **Replace Excel:** Store reps, qualifications, MRO demand, and assignments in PostgreSQL behind a FastAPI backend and a web UI.

## Open questions

Confirm these with the challenge owners:

- What are the CBA work/rest rules? For example: minimum rest between shifts, maximum consecutive days, maximum hours per week, and days off.
- How is overtime defined and paid, and should the solver limit it, minimize its cost, or spread it evenly?
- How is availability recorded? For example: vacation, training, sick leave, or existing commitments.
- What does an MRO demand record look like (aircraft type, location, date range, number of reps needed), and how far ahead is it known?
- Do travel time and cost between home base and MRO matter?
- What does the current Excel file look like, and can we get sample or anonymized data?

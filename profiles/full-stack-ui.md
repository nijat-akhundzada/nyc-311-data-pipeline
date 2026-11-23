# Full-Stack/UI Profile

Merge relevant rules into the project context.

- Treat UI controls and displayed values as contract consumers, not implicit backend requirements.
- Define loading, empty, error, unauthorized, offline, and success states.
- Build accessible, responsive component behavior against `ui-context.md`.
- Separate visual shell work from API wiring when either unit would otherwise be too broad.
- Map each user action to an authorized backend capability or explicitly disable/defer it.
- Test critical journeys at component, API integration, and end-to-end levels.
- Avoid mock data in release acceptance unless the surface is explicitly a prototype.

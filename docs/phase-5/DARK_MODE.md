# Dark Mode

## Goal
Configure a persistent, application-wide dark mode toggle. The solution must integrate seamlessly with Tailwind CSS v4 directives, prevent light-theme flashes during page loads, and respect system preferences.

## Scope
- Header navbar toggle button switching between Light and Dark modes.
- Inline theme script loading in the HTML head document structure.
- Local Storage key synchronization.
- Contrast styling updates across all dashboards, forms, and charts.

## Responsibilities
- **Frontend Developer**: Write layout toggle scripts, verify Tailwind CSS dark mode config, audit contrast levels.

## Django App(s)
`core` (base layout files)

## Files to Create / Modify
```
core/
  templates/
    base.html         # Modify to insert head script and toggle component
    partials/
      navbar.html     # Add toggle button markup
```

## Dependencies
- Phase 1 Tailwind CSS v4 setup and base template layouts.

## Business Rules
1. **Flash Prevention**: The theme checking script must execute synchronously in the `<head>` tag before any body content renders, avoiding "flash of light theme" rendering bugs.
2. **Preference Ordering**: The system evaluates configurations in this priority order:
   - First: Explicit local storage user settings (`theme: dark` or `theme: light`).
   - Second: Browser media configuration query (`prefers-color-scheme: dark`).
3. **Chart Integration**: Chart.js elements must update gridline colors and font styling options dynamically when dark mode toggles occur.
4. **Contrast Compliance**: Dark mode backgrounds must use deep grays (e.g., `#111827` or `#1F2937`) paired with high-contrast text shades to meet accessibility standards.

## Implementation Steps

### Step 1 — Embed Flash-Prevention Script in Base HTML
Place the execution script inside the head of the root document.
```html
<!-- core/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>TransitOps</title>
  
  <!-- Flash prevention script -->
  <script>
    if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark')
    }
  </script>
  
  {% block extra_head %}{% endblock %}
</head>
<body class="bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-gray-100 transition-colors duration-200">
  {% block content %}{% endblock %}
</body>
</html>
```

### Step 2 — Create the Navbar Toggle Component
```html
<!-- core/templates/partials/navbar.html -->
<button id="theme-toggle" type="button" class="text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700 rounded-lg text-sm p-2.5">
  <!-- Dark Icon (Moon) -->
  <svg id="theme-toggle-dark-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path></svg>
  <!-- Light Icon (Sun) -->
  <svg id="theme-toggle-light-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95a1 1 0 11-1.414-1.414 1 1 0 011.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zm-5.05-.464a1 1 0 11-1.414-1.414 1 1 0 011.414 1.414zm-2.12-10.607a1 1 0 011.414 0l.706.707a1 1 0 11-1.414 1.414l-.707-.707a1 1 0 010-1.414zM4 11a1 1 0 100-2H3a1 1 0 100 2h1z" fill-rule="evenodd" clip-rule="evenodd"></path></svg>
</button>

<script>
  const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
  const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');

  // Change the icons inside the button based on previous settings
  if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      themeToggleLightIcon.classList.remove('hidden');
  } else {
      themeToggleDarkIcon.classList.remove('hidden');
  }

  const themeToggleBtn = document.getElementById('theme-toggle');

  themeToggleBtn.addEventListener('click', function() {
      // Toggle icons inside button
      themeToggleDarkIcon.classList.toggle('hidden');
      themeToggleLightIcon.classList.toggle('hidden');

      // If set via local storage previously
      if (localStorage.getItem('color-theme')) {
          if (localStorage.getItem('color-theme') === 'light') {
              document.documentElement.classList.add('dark');
              localStorage.setItem('color-theme', 'dark');
          } else {
              document.documentElement.classList.remove('dark');
              localStorage.setItem('color-theme', 'light');
          }
      // If not set via local storage previously
      } else {
          if (document.documentElement.classList.contains('dark')) {
              document.documentElement.classList.remove('dark');
              localStorage.setItem('color-theme', 'light');
          } else {
              document.documentElement.classList.add('dark');
              localStorage.setItem('color-theme', 'dark');
          }
      }
  });
</script>
```

## Success Scenario
1. User loads the platform for the first time. The page renders matching system colors.
2. User toggles the theme button in the header.
3. The background swaps from white to deep gray instantly.
4. Refreshing the dashboard preserves the dark theme context.

## Definition of Done
- [ ] Theme toggling works in the browser.
- [ ] The preference settings write and read from Local Storage keys correctly.
- [ ] Inline checker is present in `<head>` to avoid layout flashes.
- [ ] Tailwind class tags utilize correct `dark:` variants.
- [ ] Elements in Flowbite and custom templates remain readable in dark layouts.

## AI Instructions
- Standardize on `dark:bg-gray-900` for main background styles and `dark:text-white` for readability.
- Do not add multiple class handlers on body tags; delegate theme transitions entirely to the root `<html>` tag.
- Ensure custom forms styling elements specify appropriate border adjustments for dark panels.

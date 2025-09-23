We need loaders:

- Emails
- Social Posts
- Work Artifacts
    - Code
    - Reports (Something created for someone else to convey some point.)
        - This should also explain "why" choice (formatting, important elements, etc.)

Each of these items should be differentiated by by area: (work, school, personal) and purpose.

We should create a standard dataset artifact like the question/answer sheet.

Then process it into a prompt/example dataset similar to a fine tuning set.

## What This Dataset Does

Here's what a personalized completion model trained on your data might suggest:

| When You're... | Starting to write... | It might complete with... |
|----------------|---------------------|-------------------------|
| **Writing a work email** | "Hey team, following up on our project deadline of" | "March 15th - that feels tight with everything on our plates. What if we pushed to March 22nd for better quality? Thoughts?" |
| **Coding a login feature** | "TODO: Add user auth to /login endpoint, need to check" | "email format, password strength, and add rate limiting. I'll use JWT tokens for sessions." |
| **Posting on LinkedIn** | "Just shipped our new feature that boosts UX by" | "cutting load times 40% and simplifying signup. Team crushed it over 3 months!" |
| **Writing a tech report** | "Analysis shows: 1) DB bottlenecks, 2)" | "Memory leaks from bad caching, 3) API latency. Fix: Add Redis + optimize queries." |
| **Taking meeting notes** | "Agenda: Q3 goals review, blockers -" | "Resource planning for next sprint, retrospective. Actions: Sarah docs, Mike dependencies." |
| **Reviewing a PR** | "This PR improves payment error handling with" | "network failure catches, correlation ID logging, friendly error messages. Tests pass, docs updated." |
| **Emailing a friend** | "Hey! Hope you're good. Weekend plans still on for" | "morning hike then that new brunch spot? Let me know if timing works!" |
| **Setting up a project** | "Setup: 1. Clone repo, 2. npm install, 3." | "Add .env vars, run migrations, npm run dev to start." |
| **Planning tasks** | "Build user dashboard - Priority: High - Time:" | "2 days - Needs: Auth module, DB updates - Must: Show stats/activity/profile editing." |
| **Writing a dev blog** | "Good dev work isn't just coding, it's" | "really getting user needs and building with empathy. Three lessons that changed my approach:" |
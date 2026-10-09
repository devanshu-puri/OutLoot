# PROJECT BLUEPRINT: REAL-WORLD EXPLORATION GAME WITH OPEN-SOURCE AI

## 1. Project Overview

### 1.1 Working Concept

Build a location-based outdoor exploration game inspired by the core gameplay loop of Pokémon GO, combined with real-world movement verification, gamified rewards, and a sponsor-powered marketplace.

The application encourages users to take breaks from their screens by exploring their surroundings, walking, and spending time outdoors. During a qualifying outdoor session, virtual items appear on a map. Users discover and collect these items, earn points according to each item's rarity and value, and eventually exchange accumulated points for sponsor-provided discounts, perks, merchandise, and other rewards.

The experience should make going outdoors feel like a game, not like completing a fitness assignment.

### 1.2 The Core Idea

The application connects four systems:

1. **Outdoor Exploration:** Users explore a map and discover virtual items at different locations.
2. **Movement Verification:** The application uses device signals to estimate whether the user is genuinely moving outdoors rather than simply leaving the app open.
3. **Gamification and Points:** Each qualifying session generates collectible items with different point values. Users accumulate points through verified exploration.
4. **Sponsor Marketplace:** Participating companies offer rewards that users can redeem using their earned points, creating a connection between real-world activity and sponsor benefits.

Open-weight AI should provide meaningful functionality within the application, rather than being added merely as a chatbot. It may personalize exploration missions, generate item narratives, create location-appropriate challenges, or adapt gameplay to user preferences.

### 1.3 Product Vision

Turn time away from screens into an enjoyable, rewarding, and socially shareable real-world experience.

### 1.4 Product Principles

* The user should spend more time outdoors than interacting with the application.
* Screen time alone must never qualify as successful participation.
* Movement verification should be privacy-conscious and reasonably resistant to abuse.
* Rewards must be transparent, achievable, and governed by explicit rules.
* Sponsors should be able to contribute real value without controlling gameplay unfairly.
* The system should be modular enough to evolve from a prototype into a production application.
* Open-weight AI should provide a demonstrable benefit to the product.

---

## 2. User Roles and Stakeholders

### 2.1 Player

A player is someone who uses the application to explore their surroundings, collect virtual items, accumulate points, and redeem rewards.

Primary capabilities:

* Create and manage an account.
* Start and complete outdoor sessions.
* View a map and discover eligible items.
* Collect items when gameplay requirements are satisfied.
* View session history, points, inventory, and achievements.
* Browse and redeem available rewards.
* View redemption history and reward conditions.

### 2.2 Sponsor

A sponsor is a company or organization that contributes discounts, perks, vouchers, merchandise, or other benefits.

Potential sponsor types include:

* Cafés and restaurants.
* Clothing and sports brands.
* Outdoor equipment companies.
* Local businesses.
* Events and recreational organizations.
* Student-focused brands and services.

Sponsor capabilities may eventually include:

* Create and manage reward offers.
* Define redemption conditions and availability.
* Set reward inventory or voucher limits.
* Monitor aggregated campaign performance.
* Verify reward redemptions.

Sponsor participation must not allow companies to purchase additional gameplay points or secretly manipulate item values.

### 2.3 Platform Administrator

The administrator operates the platform.

Responsibilities include:

* Approving sponsors and reward offers.
* Managing item definitions and point values.
* Configuring session and collection rules.
* Handling fraudulent activity and disputes.
* Monitoring system health.
* Managing abuse reports and inappropriate content.
* Reviewing reward inventory and redemption records.

### 2.4 Optional Future Roles

The architecture may support these later:

* Friend groups and cooperative exploration.
* Event organizers.
* Community challenge organizers.
* Moderators.
* Sponsor campaign managers with restricted permissions.

These are not mandatory for the first release.

---

## 3. Core Gameplay Loop

The intended player experience is:

1. The user opens the application.
2. The user starts an outdoor exploration session.
3. The application begins measuring qualifying movement.
4. The user sees a map containing eligible collectible locations or item markers.
5. The user walks around and explores the real world.
6. Items become available according to the configured timing and gameplay rules.
7. The user collects an eligible item.
8. The backend validates the collection and awards the corresponding points.
9. The current collection cycle ends or resets according to the configured rules.
10. The user continues exploring through another cycle, or ends the session.
11. Earned points are reflected in the user's account.
12. The user can browse a marketplace and redeem an eligible reward.

**Important gameplay intention:** The user should not need to keep looking at the screen while walking. The application should support short interactions before movement, minimal interactions during a session, and a clear summary afterward.

The system should also support ending a session without losing points already earned through valid collections.

---

## 4. Outdoor Sessions and Timer Mechanics

### 4.1 Session Lifecycle

A session represents one continuous attempt at outdoor exploration.

Suggested states:

* `IDLE`: No active session.
* `PREPARING`: Permission and safety checks are being completed.
* `ACTIVE`: The session is active and qualifying movement is being evaluated.
* `ITEM_AVAILABLE`: A collectible is available, if the game rules permit this state.
* `PAUSED`: The user or system has temporarily paused qualifying gameplay.
* `COMPLETED`: The session has ended normally.
* `INVALIDATED`: The session has been invalidated under an explicit, explainable rule.

The implementation may combine or rename these states, but it must preserve valid state transitions and prevent duplicate point awards.

### 4.2 Timer Design

The gameplay should distinguish between two concepts:

**A. Outdoor session time**

The total duration of the exploration session.

**B. Collection-cycle timer**

The timer controlling when another item becomes available or when the next collection cycle can begin.

For example, a configurable prototype might use a five-minute qualifying cycle. This is an example value, not a final game rule.

A possible sequence:

* The user starts an outdoor session.
* The application measures movement.
* The first collectible becomes available when the configured eligibility conditions are satisfied.
* The user collects it.
* The collection cycle resets.
* Another collectible becomes available after the next qualifying interval.
* The process continues until the user ends the session.

The design must clarify whether the interval measures elapsed time, qualifying movement time, or a combination of both. This should be a configuration rather than an unexplained hard-coded constant.

### 4.3 Timer Reset Rules

When a valid collection succeeds:

* The backend records the collection.
* The corresponding item is marked as collected.
* The correct points are awarded exactly once.
* The collection-cycle timer is reset.
* The next eligible item is scheduled or selected according to the game rules.

When a collection fails:

* The item must not be marked as collected.
* No points should be awarded.
* The timer behavior should follow a documented retry rule.

When the session ends:

* The application stops collecting movement data.
* The final session summary is generated.
* Valid earned points remain in the account.
* The session cannot be reused to collect the same item again.

The backend, rather than the frontend countdown alone, must be authoritative for eligibility and point awards.

### 4.4 Configurable Rules

The system should allow authorized administrators to configure:

* Minimum cycle duration.
* Minimum qualifying movement time.
* Item spawn timing.
* Maximum collections per session.
* Maximum points per session.
* Cooldowns between collections.
* Session duration limits.
* Rules for interruptions and paused sessions.

These settings must be configurable without requiring changes to unrelated parts of the application.

---

## 5. Map-Based Exploration and Item Discovery

### 5.1 Map Experience

The user sees a map of the relevant surrounding area with collectible items represented by visual markers.

The map may show:

* Collectible item locations.
* Items that are not yet available.
* Items currently available to collect.
* Items already collected during the session.
* The user's approximate location, subject to permission.
* Safe, accessible exploration areas when suitable data is available.

The map should encourage exploration without forcing users to follow a single fixed route.

### 5.2 Item Spawning

Items can be generated or selected according to:

* The user's current exploration area.
* A predefined spawn distribution.
* Distance from previously collected items.
* Item rarity.
* Session progress.
* Time of day, if relevant and privacy-appropriate.
* Curated event or sponsor campaigns.

For the initial prototype, use a controlled set of predefined spawn points or generated nearby coordinates. Avoid introducing complicated live map generation before the collection loop works reliably.

The backend must enforce minimum separation distances and spawn limits where necessary.

### 5.3 Item Categories

Define item categories that have different collection values.

Example categories:

| Item type     | Example point value | Intended frequency        |
| ------------- | ------------------: | ------------------------- |
| Common        |                  10 | Frequent                  |
| Uncommon      |                  25 | Moderate                  |
| Rare          |                  60 | Occasional                |
| Epic          |                 120 | Uncommon                  |
| Special event |                 200 | Limited or event-specific |

These values are illustrative and should be configurable.

Higher-value items should not automatically require users to enter dangerous, private, inaccessible, or otherwise unsuitable locations.

### 5.4 Item Data Model

Each item definition should support fields equivalent to:

* `item_id`
* `name`
* `description`
* `category`
* `rarity`
* `base_points`
* `spawn_rules`
* `collection_rules`
* `active_status`
* `event_id`, if applicable
* `visual_asset_reference`, if needed

Each spawned item instance should separately record:

* `spawn_id`
* `item_id`
* `session_id`
* `spawn_location` or a reference to a predefined location
* `spawned_at`
* `available_at`
* `expires_at`, if applicable
* `status`
* `collected_by`
* `collected_at`

Separate item definitions from spawned instances. A rare item type can have many instances, each with its own location and collection status.

### 5.5 Collection Rules

A collection should only succeed when:

* The session is eligible.
* The item exists and is currently available.
* The user satisfies the required proximity or interaction rule.
* The required movement or timing conditions have been met.
* The item has not already been collected.
* The session and item are still valid.
* The user has not exceeded configured limits.

The backend must perform the final validation.

If the user attempts to collect an item outside its valid range, the application should explain that the item is out of range rather than silently awarding or rejecting points.

---

## 6. Movement Verification and Anti-Cheating

This is a critical subsystem. The objective is to estimate whether a user has genuinely taken a movement-based break, not to claim that GPS can prove a person's identity or intentions.

### 6.1 Device Binding

The product should associate an account with an enrolled device or installation.

Potential signals include:

* An installation identifier.
* Platform-supported device integrity signals, where available.
* Session-specific identifiers.
* Server-side timestamps.
* Optional reauthentication for sensitive actions.

A device identifier alone is not proof that the same human is using the device. Device resets, reinstallations, shared devices, and privacy settings must be considered.

For the MVP, use a simple account-to-installation association and session validation. More advanced integrity checks can be added later.

### 6.2 Movement Signals

Subject to platform capabilities and user permissions, the application may use:

* GPS coordinates.
* Location accuracy estimates.
* Timestamped location samples.
* GPS-derived speed.
* Distance travelled.
* Accelerometer or step-counter data.
* Device activity recognition, if available.

The system should combine signals rather than relying on one measurement.

### 6.3 Estimating a Meaningful Break

The application needs configurable thresholds for:

* Minimum elapsed time.
* Minimum qualifying movement duration.
* Minimum displacement or accumulated distance.
* Maximum plausible movement speed.
* Acceptable location accuracy.
* Required consistency between samples.
* Maximum acceptable gaps between samples.

Illustrative example:

A session runs for ten minutes. The user has valid location samples, moves through a plausible walking route, and accumulates sufficient qualifying movement time. The session may qualify for collection eligibility.

By contrast, if the device remains stationary for most of the session, the application may pause eligibility or require additional qualifying movement.

**Do not equate every stationary period with cheating.** Users may be sitting in a park, resting, gardening, or observing wildlife. Decide explicitly whether the product rewards walking alone or outdoor activity more broadly. For a walking-focused MVP, prolonged stationary periods can pause the movement-based timer without automatically invalidating the whole session.

### 6.4 Speed Rules

Speed is one signal, not the sole source of truth.

The system may:

* Reject impossible or highly implausible movement patterns.
* Exclude low-quality location samples.
* Treat sustained vehicle-like speeds as non-qualifying for a walking mode.
* Allow plausible walking speeds with reasonable tolerance.
* Pause eligibility when evidence is insufficient.

Thresholds should be configurable and tested against actual device data. GPS can jump, drift, or report misleading speeds, particularly around buildings.

### 6.5 Anti-Abuse Rules

Potential controls:

* Validate every collection on the server.
* Prevent duplicate item collection.
* Enforce per-session and per-day limits.
* Detect impossible travel between consecutive samples.
* Ignore stale, out-of-order, or excessively inaccurate samples.
* Use idempotency keys for collection requests.
* Apply rate limits to session and collection endpoints.
* Record explainable rejection reasons.
* Maintain an audit trail for suspicious point transactions.
* Introduce stronger integrity checks only where supported by the target platform.

Do not permanently ban users solely because of one suspicious GPS sample.

### 6.6 Safety and Privacy

The application should:

* Request location permission only when needed.
* Clearly explain why location is collected.
* Prefer processing movement signals on-device where practical.
* Avoid retaining raw location histories indefinitely.
* Store only the minimum information necessary for validation and fraud prevention.
* Provide a clear session-stop control.
* Avoid requiring users to look at their phones while crossing roads.
* Never instruct users to enter private property or unsafe areas.
* Avoid publishing users' real-time locations to other players by default.

The final privacy design must account for the target operating system and applicable privacy requirements.

---

## 7. Points, Inventory, and Progression

### 7.1 Points Ledger

Points are earned through valid game actions.

The system should distinguish between:

* Points earned.
* Points redeemed.
* Promotional credits, if introduced.
* Adjustments or reversals.
* Current available balance.

The balance should be derived from an auditable transaction ledger or maintained using a consistent transactional system.

### 7.2 Awarding Points

For every successful collection:

1. Validate the session and item.
2. Verify the collection rules.
3. Obtain the authoritative item point value.
4. Create a collection record.
5. Record the point transaction.
6. Update or recalculate the user's available balance.
7. Return the confirmed result to the client.

All related operations must be atomic or protected by an equivalent consistency mechanism.

A repeated network request must not award points twice.

### 7.3 Progression

Possible future features:

* Player levels.
* Exploration streaks.
* Weekly challenges.
* Collection badges.
* Rare-item collections.
* Community milestones.
* Seasonal events.
* Personal exploration statistics.

These features should encourage healthy participation rather than pressure users to walk when unsafe, sick, or unavailable.

---

## 8. Sponsor-Powered Reward Marketplace

### 8.1 Marketplace Purpose

The marketplace connects points earned through outdoor exploration to benefits provided by sponsors.

Possible rewards:

* Percentage discounts.
* Fixed-value vouchers.
* Free products or services.
* Merchandise.
* Event tickets or experiences.
* Limited-edition digital collectibles.
* Sponsored community challenges.

A reward must have a clear description, sponsor identity, redemption cost, availability status, and terms.

### 8.2 Reward Example

Suppose a sponsor provides the following offers:

| Reward                   | Example redemption cost |
| ------------------------ | ----------------------: |
| 5% café discount         |              100 points |
| Free beverage            |              350 points |
| Branded merchandise      |            1,000 points |
| Outdoor activity voucher |            1,500 points |

These are example values, not a commitment to any real sponsor.

The platform should make it possible to change reward costs and inventory through authorized configuration.

### 8.3 Reward Lifecycle

A reward may move through these states:

* `DRAFT`
* `PENDING_APPROVAL`
* `ACTIVE`
* `OUT_OF_STOCK`
* `EXPIRED`
* `PAUSED`
* `RETIRED`

A redemption may move through these states:

* `REQUESTED`
* `CONFIRMED`
* `FULFILLED`
* `CANCELLED`
* `EXPIRED`

Only authorized transitions should be allowed.

### 8.4 Redemption Flow

1. The user opens the marketplace.
2. The application displays active, eligible rewards.
3. The user selects a reward and reviews its terms.
4. The backend checks the user's balance and reward availability.
5. The user confirms redemption.
6. The system atomically reserves the reward and deducts the required points.
7. A unique redemption record is created.
8. The user receives a voucher code, QR code, or redemption instructions.
9. The sponsor or its authorized redemption system verifies the reward.
10. The redemption is marked as fulfilled when appropriate.

If redemption fails, the system must not leave the user with an incorrect balance or an unusable reward.

### 8.5 Sponsor Management

Sponsors should be able to define:

* Reward name and description.
* Required points.
* Available quantity.
* Validity period.
* Eligible regions or locations.
* Redemption conditions.
* Campaign limits.
* Redemption verification method.

For the MVP, sponsor offers can be managed by administrators rather than requiring a separate sponsor dashboard.

### 8.6 Business Model

Possible future revenue sources:

* Sponsored reward placements.
* Sponsored exploration events.
* Brand partnerships.
* Local business campaigns.
* Paid campaign analytics using appropriately aggregated data.

Sponsors should not receive users' raw location histories. Any analytics or data sharing should be transparent and privacy-conscious.

The platform must not make rewards appear available when sponsors have not supplied or authorized them.

---

## 9. Role of Open-Weight AI

Open-weight AI should be a meaningful but bounded part of the product.

The application must remain playable when the AI model is unavailable.

### 9.1 Suitable AI Capabilities

**A. Personalized exploration missions**

Generate short outdoor challenges using:

* Available time.
* User-selected interests.
* Desired activity intensity.
* Chosen environment type.
* Previously completed mission categories.

**B. Item narratives**

Generate short descriptions, themes, or fictional lore for collectibles.

**C. Adaptive difficulty**

Suggest new challenge types based on previous completion history without increasing unsafe physical demands.

**D. Context-aware suggestions**

Suggest general types of activities appropriate to a selected environment. Do not claim to know current local conditions unless the system has reliable data to support that claim.

**E. Sponsor campaign assistance**

Help administrators draft mission descriptions and campaign text. All sponsor content must be reviewed before publication.

### 9.2 AI Constraints

The AI must not be the authority for:

* Point balances.
* Item ownership.
* Reward availability.
* Redemption success.
* Fraud determinations.
* Identity verification.
* Location verification.

These are deterministic application responsibilities.

The AI should generate structured output that is validated before use. For example, it can suggest a mission title, description, estimated duration, and completion criteria, but the backend decides whether the mission is valid.

### 9.3 Open-Innovation Requirements

The implementation should document:

* Which open-weight model is used.
* Where inference runs.
* Which application features depend on the model.
* Whether user data is sent to external services.
* What works without internet connectivity.
* How another compatible model could be substituted.
* What the model's license permits.
* What hardware and latency are required.

For an initial local prototype, a compatible Gemma model served through Ollama is one possible option. The final choice should depend on the available hardware, model capabilities, licensing, and latency requirements.

---

## 10. MVP Scope

The first release should validate the core gameplay loop before implementing a large social platform.

### Must Have

* Account or prototype user identity.
* Permission-based location access.
* Start, pause, and end session controls.
* Map display with collectible markers.
* A small configurable item catalogue.
* Collection-cycle timer.
* Basic movement qualification.
* Server-side collection validation.
* Point awarding with duplicate prevention.
* Point balance and transaction history.
* Basic marketplace.
* A small number of sample sponsor rewards.
* Reward redemption with unique identifiers.
* Local AI integration for at least one meaningful feature.
* Error handling and a basic test suite.
* Clear privacy and safety messaging.

### Should Have

* Session history.
* Collection inventory.
* Daily limits.
* Better GPS-quality handling.
* Configurable movement thresholds.
* Reward inventory management.
* Admin controls for item values and rewards.
* Offline-friendly gameplay design.
* Structured logs and basic monitoring.

### Future Features

* Friends and group exploration.
* Leaderboards.
* Team challenges.
* Sponsor dashboards.
* Live sponsor campaigns.
* Advanced device-integrity checks.
* More sophisticated AI personalization.
* Cross-platform support.
* Community-created missions.
* Richer collectible visuals and animations.

Do not delay a working MVP to build every future feature.

---

## 11. Technical Architecture Requirements

The implementation agent should choose a suitable architecture and technology stack after inspecting the available development resources.

Do not assume a specific frontend framework, backend language, database, map provider, authentication provider, hosting platform, or AI framework without evaluating the project requirements.

The architecture must account for these logical components:

1. **Client application:** UI, map, permissions, local session state, and user interaction.
2. **Session service:** Session lifecycle, timer rules, and movement qualification.
3. **Location and movement subsystem:** Sensor sampling, location quality, and movement evidence.
4. **Item service:** Spawn generation, item availability, proximity, and collection rules.
5. **Points service:** Transaction ledger, balances, and point-award idempotency.
6. **Marketplace service:** Reward catalogue, inventory, and redemption.
7. **Sponsor administration:** Sponsor offers, approvals, and campaign management.
8. **AI service:** Model interaction, structured generation, validation, and fallback behavior.
9. **Persistence layer:** Users, sessions, items, transactions, rewards, and redemptions.
10. **Observability and security:** Logs, error tracking, authorization, rate limits, and audit records.

The implementation may combine these components in a modular monolith for the MVP. Microservices should only be introduced if actual scaling or organizational requirements justify the added complexity.

### Architecture Quality Requirements

* Clear separation between business rules and UI logic.
* Server-authoritative validation of collections and redemptions.
* Secure handling of account and session credentials.
* Atomic point transactions.
* Duplicate-request protection.
* Schema validation for AI-generated output.
* Explicit error handling and retry behavior.
* Configurable game rules.
* Automated tests for important state transitions.
* A documented local development setup.
* Reproducible configuration through environment variables or equivalent mechanisms.
* No secrets committed to source control.

---

## 12. Data Model Expectations

The implementation agent should propose the final database schema, relationships, indexes, and data-retention policies.

At minimum, consider these entities:

| Entity               | Purpose                                                  |
| -------------------- | -------------------------------------------------------- |
| `User`               | Account identity, preferences, and status                |
| `DeviceInstallation` | Installation association and relevant integrity metadata |
| `Session`            | Start/end times, state, and gameplay configuration       |
| `MovementEvidence`   | Minimum necessary movement-validation data               |
| `ItemDefinition`     | Reusable item types and point values                     |
| `SpawnedItem`        | A specific item available during a session               |
| `Collection`         | Record of a successful or attempted collection           |
| `PointTransaction`   | Auditable earning, spending, or adjustment               |
| `Reward`             | Sponsor offer and redemption conditions                  |
| `Sponsor`            | Organization and approval status                         |
| `Redemption`         | Reward claim, status, and verification data              |
| `Challenge`          | Optional missions, events, and completion criteria       |
| `AuditEvent`         | Security-sensitive or administrative activity            |

The implementation should identify which data is authoritative, which can be cached, which requires transactional consistency, and which should expire.

Do not store full location histories unless there is a documented necessity and an appropriate retention policy.

---

## 13. Testing and Acceptance Criteria

The project is not complete merely because the map and interface render correctly.

### Gameplay

* A user can start and end a session.
* Items appear according to the configured rules.
* Collection requires a valid session and an eligible item.
* An invalid or out-of-range collection does not award points.
* A valid collection awards the configured points exactly once.
* The collection-cycle timer resets according to the documented rules.
* Ending a session preserves valid earned points.

### Movement

* Poor-quality location samples do not automatically qualify a session.
* Implausible movement patterns can be flagged or excluded.
* Stationary periods follow the defined policy.
* Temporary GPS loss is handled predictably.
* The user can stop tracking.
* Movement data is not exposed to unauthorized users.

### Points and Marketplace

* The displayed balance agrees with the transaction ledger.
* Concurrent collection requests cannot duplicate points.
* Concurrent redemption requests cannot spend the same points twice.
* Expired or unavailable rewards cannot be redeemed.
* Failed redemption attempts do not incorrectly deduct points.
* Every confirmed redemption has a unique identifier.
* Administrative point adjustments are auditable.

### AI

* Valid model output produces a usable mission.
* Invalid or unsafe output is rejected or corrected.
* Model timeouts do not corrupt gameplay.
* Core collection and redemption functionality remains available without AI.
* The implementation documents whether AI inference is local or remote.

### Product Experience

* The user can understand the game rules before beginning.
* The interface does not encourage unsafe phone use while walking.
* Permissions and data collection are explained.
* A user can complete the main gameplay loop and understand their earned rewards.

---

## 14. Implementation Plan

The implementation agent should produce a phased plan and then execute it incrementally.

### Phase 1: Requirements and Feasibility

* Inspect the available hardware, runtime environment, libraries, and development constraints.
* Identify the target platforms.
* Resolve ambiguous timer and movement rules.
* Select a map strategy.
* Assess local AI model compatibility.
* Document assumptions and risks.
* Recommend a technology stack with reasons.

### Phase 2: Core Gameplay Prototype

* Implement the map and sample item locations.
* Build session lifecycle controls.
* Implement the collection-cycle timer.
* Implement item availability and collection validation.
* Award points and record collections.
* Test the main gameplay loop using simulated movement data.

### Phase 3: Real Movement Validation

* Integrate the relevant device location APIs.
* Handle permission denial and GPS errors.
* Implement movement qualification.
* Test stationary, walking, noisy GPS, and implausible-speed cases.
* Ensure the system does not rely on client-side claims alone.

### Phase 4: Points and Marketplace

* Implement the point ledger.
* Build reward listings.
* Implement inventory reservation and redemption.
* Add unique redemption identifiers.
* Create sample sponsor offers.
* Test transaction consistency.

### Phase 5: Open-Weight AI

* Integrate the selected model.
* Add structured mission generation.
* Validate model output.
* Add deterministic fallback missions.
* Measure latency and hardware requirements.
* Demonstrate which features work locally without cloud AI.

### Phase 6: Hardening and Demo

* Add authentication and authorization appropriate to the selected platform.
* Test failure scenarios and duplicate requests.
* Add privacy controls and data retention rules.
* Improve mobile usability and outdoor safety.
* Document installation and execution.
* Prepare a reproducible demo and a truthful account of offline functionality.

The agent should not attempt to implement the entire product in one enormous code-generation step. Each phase should produce a runnable, testable increment.

---

## 15. Expected Deliverables From the Implementation Agent

Before coding, return:

1. A concise interpretation of the product.
2. A list of ambiguities and proposed defaults.
3. A resource-aware technology-stack recommendation.
4. An architecture diagram.
5. A proposed database schema.
6. A breakdown of backend, frontend, map, movement, AI, and marketplace responsibilities.
7. A phased implementation plan.
8. Key risks and mitigations.

During implementation, deliver:

1. A working application.
2. A clear project directory structure.
3. Environment configuration instructions.
4. Database setup and migrations, where applicable.
5. Automated tests.
6. Sample data for items, users, and sponsor rewards.
7. Error-handling and security controls.
8. A README with setup, run, and test commands.
9. A list of implemented, incomplete, and deferred features.

At completion, document:

* What actually works.
* What was tested.
* Known limitations.
* What requires external credentials, hardware, permissions, or services.
* Whether the app works offline and under exactly what conditions.
* How the open-weight AI contributes to the application.

Do not claim a feature is implemented or tested unless it actually is.

---

## 16. Important Product Decisions the Agent Must Resolve

Before finalizing the implementation, evaluate these decisions and recommend defaults based on the available resources.

### A. What does the timer measure?

Should the collectible become available after:

* A fixed elapsed interval?
* A minimum amount of qualifying walking?
* A combination of elapsed time and movement?

The implementation must make the selected rule explicit.

### B. What counts as a valid break?

Should the game reward only walking, or should it also support stationary outdoor activities such as gardening and birdwatching? These require different validation models.

### C. How should items appear on the map?

Should the MVP use:

* Predefined spawn points?
* Randomized points within eligible areas?
* A combination of curated locations and procedural spawning?

Prioritize safety, predictability, and implementation simplicity.

### D. What is the relationship between points and sponsor rewards?

Determine whether points are:

* A non-transferable gameplay score.
* Redeemable platform credits.
* A broader loyalty mechanism.

For the initial release, treat points as non-transferable, non-cash gameplay credits with no cash-out feature. Clearly disclose reward terms and do not imply that points have a guaranteed monetary value.

### E. How will offline gameplay work?

Decide what remains functional without connectivity:

* Session timing.
* Movement measurement.
* Item discovery.
* Temporary collection records.
* Point synchronization.
* Reward redemption.

A locally running model alone does not make the entire game offline-capable. Offline point awards and later synchronization require explicit protection against duplicate or fabricated transactions.

### F. What is the initial target platform?

Evaluate the feasibility of:

* Android-first development.
* Cross-platform mobile development.
* A web prototype for validating gameplay before mobile implementation.

Real background location and sensor behavior must be evaluated on the actual target platform. A browser-based prototype should not be assumed to have the same capabilities as a native mobile application.

### G. What is the initial sponsor arrangement?

For the prototype, use administrator-created sample rewards. Real sponsor onboarding, payment systems, automated voucher issuance, and partner dashboards should be separate milestones.

---

## 17. Definition of Success

The product succeeds when it demonstrates all of the following:

1. A user can begin an outdoor exploration session.
2. The application evaluates qualifying movement according to explicit rules.
3. Eligible virtual items become collectible.
4. Successful collections award the correct points without duplication.
5. The user can see their accumulated points.
6. The user can redeem points for a valid sample sponsor reward.
7. At least one meaningful feature uses open-weight AI.
8. The system remains understandable, testable, and reasonably resistant to common abuse.
9. The core experience encourages real-world activity rather than prolonged screen engagement.
10. The implementation clearly documents what works offline and what requires connectivity.

The project should be judged by a working, demonstrable end-to-end experience—not by the number of technologies used.

---

## 18. Final Instructions to the Implementation Agent

Treat this document as the product vision and functional requirements, not as a command to use a predetermined technology stack.

Inspect the available development environment, organizational resources, hardware, platform requirements, and existing code before choosing technologies.

Prefer the simplest architecture that satisfies the requirements and leaves a clear path for future growth.

Preserve the core gameplay idea: **explore the real world, discover virtual items, earn points through validated outdoor participation, and redeem those points for meaningful sponsor-provided rewards.**

Make the screen the shortest part of the experience.

Use open-weight AI for a genuine product capability, keep critical game and reward rules deterministic, prioritize user privacy and physical safety, and build the product in testable increments.

If a requirement is ambiguous, document the ambiguity, recommend a sensible default, and distinguish that recommendation from an explicitly established product requirement. Do not silently invent major product rules or build optional features at the expense of the core experience.

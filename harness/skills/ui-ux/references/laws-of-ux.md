# Laws of UX (all 30)

The complete lawsofux.com index (30 entries). Definitions are quoted from the source. "Apply" is the takeaway to act on; "Violation" is what reviewers flag.

## Aesthetic-Usability Effect
- **Definition:** Users often perceive aesthetically pleasing design as design that's more usable.
- **Apply:** Ship polished, consistent visuals (tokens, alignment, spacing rhythm). Aesthetics buy tolerance for minor issues but can mask real ones, so run usability checks on the task, not the looks.
- **Example:** A well-aligned onboarding screen is rated easier than an identical flow with ragged spacing.
- **Violation:** Treating positive "looks great" feedback as proof the flow works.

## Choice Overload
- **Definition:** The tendency for people to get overwhelmed when they are presented with a large number of options.
- **Apply:** Prioritize what is shown (featured or recommended option), offer search and filters up front, and use side-by-side comparison when comparison is necessary (for example, pricing tiers).
- **Example:** A pricing page with 3 tiers and a highlighted "Most popular" option.
- **Violation:** Dumping 40 unfiltered options into one dropdown or grid.

## Chunking
- **Definition:** A process by which individual pieces of an information set are broken down and then grouped together in a meaningful whole.
- **Apply:** Group content into visually distinct modules with clear hierarchy. Format long strings (phone numbers, IBANs, codes) in chunks.
- **Example:** `+1 555 123 4567` instead of `15551234567`. Settings split into titled sections.
- **Violation:** Walls of undifferentiated text, or one 30-field form with no sections.

## Cognitive Bias
- **Definition:** A systematic error of thinking or rationality in judgment that influences our perception of the world and our decision-making ability.
- **Apply:** Expect users and designers to rely on mental shortcuts (confirmation bias, anchoring, defaults). Validate designs with data, not intuition. Never exploit biases with dark patterns.
- **Example:** Testing a redesign against the baseline instead of trusting stakeholder preference.
- **Violation:** Pre-checked upsell boxes, confirmshaming ("No thanks, I like paying more").

## Cognitive Load
- **Definition:** The amount of mental resources needed to understand and interact with an interface.
- **Apply:** Remove extraneous load (decorative noise, redundant elements, unclear labels). Support intrinsic load with defaults, progressive disclosure, and visible context.
- **Example:** A checkout that prefills known data and hides rarely used fields behind "Add company details".
- **Violation:** Competing animations, several CTAs of equal weight, jargon labels.

## Doherty Threshold
- **Definition:** Productivity soars when a computer and its users interact at a pace (<400ms) that ensures that neither has to wait on the other.
- **Apply:** Give feedback within 400 ms. Use optimistic UI, skeletons, and progress indicators to improve perceived performance.
- **Example:** A "Like" toggles instantly (optimistic) and reconciles with the server afterward.
- **Violation:** A button with no pressed or loading state while a 2-second request runs.

## Fitts's Law
- **Definition:** The time to acquire a target is a function of the distance to and size of the target.
- **Apply:** Make targets large enough (at least 24x24 CSS px web, 44x44 pt iOS, 48x48 dp Android), space them apart, and place frequent actions within easy reach (screen edges and corners on desktop, thumb zone on mobile).
- **Example:** Full-width primary button at the bottom of a mobile form.
- **Violation:** 16 px icon buttons packed edge to edge. A destructive action adjacent to the primary one.

## Flow
- **Definition:** The mental state in which a person performing some activity is fully immersed in a feeling of energized focus, full involvement, and enjoyment.
- **Apply:** Match challenge to skill, give immediate feedback on every action, and remove unnecessary friction (interruptions, modals, slow responses).
- **Example:** An editor that autosaves silently instead of interrupting with save prompts.
- **Violation:** Interrupting a task with a newsletter modal or a surprise re-login.

## Goal-Gradient Effect
- **Definition:** The tendency to approach a goal increases with proximity to the goal.
- **Apply:** Show clear progress (steps, percent, checklist). Give credit for work already done.
- **Example:** "Step 3 of 4" in a checkout. A profile-completion meter that starts partly filled.
- **Violation:** A multi-step flow with no indication of length or position.

## Hick's Law
- **Definition:** The time it takes to make a decision increases with the number and complexity of choices.
- **Apply:** Minimize choices when response time matters, break complex tasks into steps, highlight a recommended option, and use progressive onboarding. Do not simplify to the point of abstraction.
- **Example:** One primary CTA per screen. Advanced options collapsed.
- **Violation:** A toolbar of 20 unlabeled icon buttons of equal weight.

## Jakob's Law
- **Definition:** Users spend most of their time on other sites. This means that users prefer your site to work the same way as all the other sites they already know.
- **Apply:** Use established conventions (logo links home, cart top-right, search icon is a magnifier, platform navigation patterns). When redesigning, let users keep a familiar version for a limited time.
- **Example:** Standard checkout: cart, shipping, payment, review.
- **Violation:** A novel gesture-only navigation or a custom scrollbar that breaks expectations.

## Law of Common Region
- **Definition:** Elements tend to be perceived into groups if they are sharing an area with a clearly defined boundary.
- **Apply:** Use cards, borders, or background fills to group related content and controls.
- **Example:** Each product in a grid sits on its own card surface.
- **Violation:** A button visually inside card A that acts on card B.

## Law of Proximity
- **Definition:** Objects that are near, or proximate to each other, tend to be grouped together.
- **Apply:** Keep related items close (label to field, heading to its section) and put more space between unrelated groups. Recheck grouping at every breakpoint.
- **Example:** Field label 4-8 px above its input and 24 px+ between fields.
- **Violation:** A label equidistant between two inputs. A heading closer to the previous section than to its own.

## Law of Prägnanz
- **Definition:** People will perceive and interpret ambiguous or complex images as the simplest form possible.
- **Apply:** Prefer simple, regular shapes and icons. Reduce visual complexity so the structure is read at a glance.
- **Example:** Simple geometric icons from one consistent icon set.
- **Violation:** Detailed illustrative icons at 16 px that read as blobs.

## Law of Similarity
- **Definition:** The human eye tends to perceive similar elements as a complete picture, shape, or group, even if those elements are separated.
- **Apply:** Style elements with the same function identically (color, shape, size). Differentiate links and navigation from body text.
- **Example:** All links share one color plus underline. All destructive actions share the danger style.
- **Violation:** Two visually identical buttons that do very different things. Links styled like plain text.

## Law of Uniform Connectedness
- **Definition:** Elements that are visually connected are perceived as more related than elements with no connection.
- **Apply:** Connect related items with lines, arrows, frames, or shared color (steppers, timelines, grouped toggles).
- **Example:** A stepper whose steps are joined by a line.
- **Violation:** A connector line that visually links unrelated items.

## Mental Model
- **Definition:** A compressed model based on what we think we know about a system and how it works.
- **Apply:** Match the user's model (carts, folders, inboxes) instead of the implementation model (tables, jobs, IDs). Use research to close the gap.
- **Example:** "Trash" that can be restored, matching the desktop model.
- **Violation:** Exposing database states such as "status=3" or "PENDING_SYNC" in the UI.

## Miller's Law
- **Definition:** The average person can only keep 7 (plus or minus 2) items in their working memory.
- **Apply:** Chunk content into small groups. Do not use "the magical number seven" to justify arbitrary limits such as capping navigation at 7 items.
- **Example:** A 16-digit card number shown as 4 groups of 4.
- **Violation:** Asking users to remember a code from a previous screen.

## Occam's Razor
- **Definition:** Among competing hypotheses that predict equally well, the one with the fewest assumptions should be selected.
- **Apply:** Avoid complexity in the first place. Remove every element that does not compromise function. The design is done when nothing more can be removed.
- **Example:** Replacing a 3-screen wizard with one inline form.
- **Violation:** Adding a settings toggle instead of choosing a good default.

## Paradox of the Active User
- **Definition:** Users never read manuals but start using the software immediately.
- **Apply:** Put guidance in context (tooltips, inline hints, empty-state tips) so users learn while doing.
- **Example:** An empty dashboard that says "Connect a data source to see charts" with a button.
- **Violation:** A mandatory 6-slide tutorial before any use.

## Pareto Principle
- **Definition:** For many events, roughly 80% of the effects come from 20% of the causes.
- **Apply:** Focus effort on the few flows and features used by most users. Optimize and test those first.
- **Example:** Making "search" and "reorder" the top of the home screen because analytics show they dominate.
- **Violation:** Polishing rarely used settings while the core task stays slow.

## Parkinson's Law
- **Definition:** Any task will inflate until all of the available time is spent.
- **Apply:** Make tasks take less time than users expect: autofill, sensible defaults, saved payment and address, one-tap reorder.
- **Example:** `autocomplete` attributes so the browser fills the address form.
- **Violation:** Forcing manual re-entry of data the system already knows.

## Peak-End Rule
- **Definition:** People judge an experience largely based on how they felt at its peak and at its end.
- **Apply:** Design the most intense moments and the final moment (confirmation, success, error recovery) deliberately. Negative moments are recalled more vividly.
- **Example:** A clear, warm order-confirmation screen with next steps.
- **Violation:** A flow that ends on a raw error or a blank page.

## Postel's Law
- **Definition:** Be liberal in what you accept, and conservative in what you send.
- **Apply:** Accept varied input formats (spaces or dashes in phone and card numbers, any case in emails), normalize them, define boundaries, and give clear feedback. Output consistent, predictable formats.
- **Example:** A phone field that accepts `(555) 123-4567` and `5551234567`.
- **Violation:** Rejecting a card number because it contains spaces.

## Selective Attention
- **Definition:** The process of focusing our attention only to a subset of stimuli in an environment — usually those related to our goals.
- **Apply:** Guide attention to what matters. Do not style content like ads (banner blindness). Avoid simultaneous competing changes (change blindness) and signal important changes clearly.
- **Example:** An inline success message next to the saved field rather than a banner at the top.
- **Violation:** Critical notices inside a banner-shaped box in an ad-like position.

## Serial Position Effect
- **Definition:** Users have a propensity to best remember the first and last items in a series.
- **Apply:** Put the most important items first and last in lists and navigation. Put the least important in the middle.
- **Example:** Bottom navigation with Home first and Profile last.
- **Violation:** Burying the primary destination in the middle of a long menu.

## Tesler's Law
- **Definition:** For any system there is a certain amount of complexity which cannot be reduced.
- **Apply:** Move inherent complexity from the user to the system (smart defaults, inference, automation). Do not design for an idealized rational user.
- **Example:** Detecting the card type from its number instead of asking.
- **Violation:** Asking users for information the system can derive (city from postal code where reliable).

## Von Restorff Effect
- **Definition:** When multiple similar objects are present, the one that differs from the rest is most likely to be remembered.
- **Apply:** Make the key action or information visually distinct, with restraint. Never rely on color alone. Be careful with motion as a differentiator.
- **Example:** One filled primary button among outlined secondary buttons.
- **Violation:** Everything highlighted, so nothing stands out. A "new" state shown only by a color change.

## Working Memory
- **Definition:** A cognitive system that temporarily holds and manipulates information needed to complete tasks.
- **Apply:** Keep the memory burden on the system: carry information across screens, differentiate visited links, show breadcrumbs, and provide comparison tables.
- **Example:** A booking summary that stays visible while the user picks seats.
- **Violation:** "Enter the code shown on the previous page."

## Zeigarnik Effect
- **Definition:** People remember uncompleted or interrupted tasks better than completed tasks.
- **Apply:** Show clear signifiers of additional content and progress toward completion. Save drafts so interrupted tasks can resume.
- **Example:** "Your profile is 60% complete: add a photo."
- **Violation:** Losing form progress on navigation away.

## Sources
- https://lawsofux.com/ (index and each law's page, including takeaways)

# Project Yellow — Trainer Portrait Style Bible
**Version:** 1.0  
**Status:** Approved working standard for new portrait proposals; individual designs still require approval  
**Scope:** Battle portraits, trainer-class presentation, and related verification  
**Owner:** Project Yellow  
**Change policy:** Record each exception or revision explicitly. Do not silently redefine the style.

## 1. Purpose and design promise
Create a consistent, polished, recognizably Generation 1 / Pokémon Yellow-inspired roster of trainer battle portraits. Treat the effort as a **controlled remaster**, not an unrelated redesign. Original artwork anchors class identity; all new and refreshed art must belong to one visual system.

The standard applies to regular trainer classes and their gender counterparts, and may extend to Gym Leaders, Elite Four, rival, bosses, and other special trainers. Overworld sprites, Pokémon sprites, and unrelated UI are separate workstreams unless a specific change is approved.

## 2. Non-negotiable rules
1. **Original first:** retrieve the actual original sprite from the repository and include it in the design review. Generated mockups or recolored reference sheets never replace source assets.
2. **Class over character:** counterparts must read as the same profession/archetype, not resemble the player character or an unrelated NPC.
3. **Consistency over detail:** never increase a sprite's polish, anatomy detail, gradients, or texture beyond what the roster can support coherently.
4. **One approved source of truth:** maintain the approved concept, final indexed master, placement metadata, and evidence separately. Mockups are never described as tested emulator captures.
5. **Preserve gameplay:** retain class/opponent IDs, party data, payouts, encounter behavior, AI, music, and event scripts unless a separate design change explicitly authorizes them.
6. **Prefer reuse:** avoid adding trainer classes. Prefer an approved rename, re-theme, or presentation variant in an existing class slot when mechanically appropriate.
7. **No silent releases:** existing artwork remains recoverable; changes live on feature branches and are not merged without approval and green tests.

## 3. Pixel-art language
**Format:** 56×56-pixel battle portrait; one master with at most four indexed grayscale shades, compatible with RGBDS conversion and DMG rendering. CGB uses palettes applied to the indexed graphics; do not assume a full-color illustration can be represented by the original graphics format.

**Silhouette:** clear at native scale; bold outer contour; readable head, limbs, hands, clothing, and signature prop. Use simple, purposeful negative space.

**Anatomy and faces:** stylized, compact Gen 1 proportions, minimal readable expressions and facial details. Avoid overly polished anime faces, intricate anatomy, or player-character lookalikes.

**Shading:** deliberate clusters and high-contrast forms; simple directional light; no blurred edges, noisy dithering, smooth gradients, automatic antialiasing, isolated stray pixels, or excessive single-pixel texture.

**Pose:** recognizable class attitude with strong action/readability. Pairs may have different poses if they convey comparable class energy and visual weight.

**Clothing and props:** preserve iconic items from the original portrait. Make gender presentation changes through recognizable clothing variations, proportions, hair, and pose—not by losing core class motifs.

**Palette:** the four-shade master is authoritative. DMG and CGB visual previews are presentation aids; actual CGB-mode colors must be measured in an emulator before claiming a custom color result.

## 4. Pairing policy
- Develop standard male/female pairs together and compare them **side by side at identical scale**. Refresh an existing portrait if necessary to achieve consistency.
- Share the same class identity, costume vocabulary, silhouette family, pixel density, contour weight, and shading approach.
- Permit different body types, personalities, accessories, and poses, but keep complexity balanced.
- Preserve the approved counterpart names; use the existing presentation-variant mechanism instead of assigning new class IDs unless a technical audit and explicit authorization justify otherwise.
- Do not retroactively change an approved original sprite simply because a counterpart was added; present the proposed pair refresh for separate approval.
- Existing pair progress is engineering evidence, not blanket art approval. Previously committed portraits may be revisited under this v1.0 standard.

## 5. Class transformation and gym alignment
**Default:** retain the original class. A re-theme is eligible when it improves a revised gym or world location and preserves clarity.

**Order of preference:**
1. Reassign an existing class with no new ID.
2. Revise costume and pose while keeping class name/identity.
3. Rename or re-theme an existing class slot with reviewed map/dialogue/party implications.
4. Introduce a class or separate variant only if existing slots cannot serve the concept.

**Transformation proposal must specify:** current class and usage locations, proposed concept, which gender variants are affected, gym/world justification, affected names/sprites/music/scripts/parties, compatibility impact, and rollback plan.

**Major characters:** Gym Leaders, Elite Four, rival, and bosses can receive stronger individual personality, but must still share the project's pixel-art rules. They are not gender-swapped by default. Revised gym themes may motivate redesign; such changes require an individual concept approval.

**Prohibited shortcuts:** reusing an unrelated trainer image under a new name; repurposing a widely used class without checking its other appearances; adjusting battle data accidentally through cosmetic changes.

## 6. Approval checkpoints (hard gates)
**Gate A — Class brief approved:** identify original asset, counterpart name, class/gym role, signature features, and any intended transformation.

**Gate B — Matched concept approved:** show actual original art next to proposed counterpart (and refreshed original, if applicable) at equal displayed scale. Call out pose and identity differences. User explicitly approves the design.

**Gate C — Pixel master approved:** show the true 56×56, max-four-shade indexed master at native size and nearest-neighbor enlargement. Check silhouette, stray pixels, value separation, facial readability, and pair cohesion. User approves major visual changes.

**Gate D — Technical insertion verified:** save PNG and derived graphics under predictable names, wire pointers and correct ROM bank, preserve class IDs/party mapping, and build regular and DEBUG ROMs. No sprite-only “pass” if bank/loader fails.

**Gate E — Gameplay evidence verified:** deterministic PyBoy controller-driven encounter, correct displayed class-name bytes, correct original or approved party species/levels, correct portrait pointer **and bank**, actual screenshot, and pixel-level comparison of the rendered portrait against the approved master. Existing trainer regressions remain green.

**Gate F — Closure approved:** evidence and screenshots saved, pass/fail counts reported truthfully, user accepts pair and any scope exceptions, and merger status is explicitly recorded. CGB appearance is a separate gate when color behavior is in scope.

If any gate fails: record the failure, fix only the supported cause, rerun all relevant regressions, and do not declare completion prematurely.

## 7. Standard production checklist
### Class discovery
- [ ] Pull original 56×56 portrait from source and verify file path
- [ ] Check where the class is used and whether gym re-theming is planned
- [ ] Confirm approved names/variants and whether both portraits need refreshing
- [ ] Record class signature features, props, silhouette, and pose energy

### Concept and art review
- [ ] Show original and counterpart side by side at matched scale
- [ ] Compare class identity, silhouette, faces, pose, and shading density
- [ ] Remove player-character resemblance and off-era styling
- [ ] Obtain explicit concept approval
- [ ] Convert to authentic 56×56 four-shade master (no resize blur)
- [ ] Obtain final pixel-art approval

### Source and integration
- [ ] Preserve original assets for rollback
- [ ] Use stable filenames and record image hash and class mappings
- [ ] Verify 56×56 dimensions and at most four grayscale indices
- [ ] Convert with RGBDS; validate PNG encoding and transparency/background
- [ ] Add portrait pointer/ROM-bank handling; check bank capacity
- [ ] Keep release encounters unchanged unless separately approved
- [ ] Use isolated DEBUG fixture; ensure source event/text ID constraints hold
- [ ] Build standard ROM and DEBUG ROM cleanly

### Emulator validation
- [ ] Use genuine controller inputs and record route/interaction trace
- [ ] Confirm trainer class ID + presentation variant
- [ ] Verify exact displayed name bytes
- [ ] Verify original/approved party count, species, and levels
- [ ] Verify portrait pointer and correct graphics bank
- [ ] Save actual nonblank battle screenshot
- [ ] Compare 56×56 rendered pixel indices against approved master (palette normalization allowed)
- [ ] Run previous sprite regressions and smoke tests
- [ ] Run CGB-mode capture and measure actual palette when required
- [ ] Attach test report/screenshots and verify all CI results

### Completion
- [ ] Archive original, approved concept, master, and test evidence
- [ ] Update trainer-pair status and change registry
- [ ] Note any class transformations and special exceptions
- [ ] Request merge separately; never infer merge approval from passing CI

## 8. Pair record template
| Field | Entry |
|---|---|
| Class slot / class ID | |
| Display names | |
| Original portrait asset | |
| Pair source/reference | |
| Gym or world role | |
| Shared identity features | |
| Approved pose(s) | |
| Master PNG files | |
| Variant mapping / ROM bank | |
| Class transformation approved? | No / Yes + link |
| Concept approved by / date | |
| Pixel master approved by / date | |
| Live test run / commit | |
| Name / party / pointer / pixels | Pending / Pass / Fail |
| DMG / CGB rendering | Pending / Pass / Not in scope |
| Merge state | Draft / Approved / Merged |

## 9. Exceptions, quality control, and automation
- Every deviation from dimensions, palette limits, class mapping, roster style, or testing requirements needs a written proposal and explicit approval.
- A matching pixel test proves the intended image rendered; **it does not prove artistic consistency**. Human approval remains essential.
- Automate asset checks, source edits, bank-space diagnostics, DEBUG fixture generation, PyBoy navigation and assertions, screenshots, and report compilation **only after several independently approved pairs validate a stable pattern**.
- Keep art-direction judgment, pair approval, class transformation, and major gym/thematic changes human-led.
- Record each automation script's inputs, assertions, rollback behavior, and CI status to avoid unverifiable “success” claims.

## 10. Definition of done
A portrait or pair is *complete* only if it has an approved class brief and final sprite, is integrated without unapproved gameplay changes, builds on supported targets, passes deterministic gameplay and pixel verification, preserves prior regressions, and has archived evidence. Optional CGB custom coloration must not be claimed unless its actual emulator palette has been tested.

---
**Next production step:** Audit the Sailor class pair against the *actual* original Sailor portrait, decide whether the original also needs a controlled refresh, and approve both silhouettes before generating final masters.

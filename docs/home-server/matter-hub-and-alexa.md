# Matter bridge & Alexa / Google voice control

How Home Assistant entities reach Alexa (or Google Home / Apple Home) through the **Home Assistant
Matter Hub** add-on, why a voice phrase that used to work stops working, and how to tell whether the
fault is in Home Assistant or in the assistant.

## The chain

```
HA entity --(carries the exposure label)--> Matter Hub add-on --> one Matter "bridge" node --> Alexa / Google / Apple
```

- The add-on publishes the entities that carry a given **label**. Label the **entities**, not the
  devices.
- The "expose to Assist" setting (voice assistant in HA itself) is a *different* axis — the bridge
  only looks at the label.
- Every published entity becomes a numbered **endpoint** inside a single bridge node. The assistant
  keeps its own copy of each endpoint: a name, a category, and a **room** you assign in its app.

## Voice phrases resolve in two different ways

This is the part that makes "it worked yesterday" possible:

- **Exact device name** — the assistant matches the words against the name in its own device list.
- **Generic phrase + place** (e.g. *"turn off the light in the kitchen"*) — the assistant resolves by
  **category + room**: the accessory must be a *light* **and** be assigned to that room **in the
  assistant's app**.

So the two paths can disagree. When the assistant re-imports an accessory, the name still matches
while the room assignment is gone — and you get *"this action isn't supported"* for the generic
phrase, while saying the device name out loud keeps working perfectly:

| Phrase | What it relies on | Works after a re-import? |
|---|---|---|
| *"turn off the kitchen lamp"* (device name) | the name in the assistant's device list | ✅ yes |
| *"turn off the light in the kitchen"* (generic + place) | category **+ room** assignment | ❌ no, until the room is re-assigned |

## Why renaming an entity ID breaks the generic phrase

- The bridge derives each endpoint from the **entity ID**. When the ID changes, it drops the old
  endpoint and re-creates it under a **new number** (its own log: *"Removing endpoint <old id> …
  controllers will see a new number if it returns"*).
- The assistant treats that as a newly discovered device: same name, but its **room / group
  membership does not survive**. There is usually **no duplicate or orphan device** to delete — the
  device is there, it just isn't in the room any more.
- This is expected churn, not a bug on either side. It also means: **batch every rename that touches
  an exposed entity, then re-sync once**, instead of renaming across many sessions.

## Fix — always on the assistant side, never in Home Assistant

1. Open the device in the assistant's app and **re-assign its room**. That is the fix in the common
   case, and it takes effect immediately.
2. Delete duplicates **only if** you actually find some (the rarer case), then re-discover.
3. Restarting the bridge add-on forces one clean re-import — but it does **not** restore rooms by
   itself.

## Debugging "the voice command does nothing"

1. **Exonerate Home Assistant first.** Turn the entity on/off in HA (or call the service) and read
   the state back. If HA works, the fault is on the assistant side.
2. **Check the label** — an entity that lost its exposure label disappears from the assistant.
3. **Read the bridge add-on's log.** It prints every endpoint it dropped and every command it
   executed (`[light.xxx] Turning OFF -> homeassistant.turn_off`), which tells you whether the
   command ever arrived at HA.
4. **Find out what the assistant is actually driving.** The *Alexa Media Player* integration imports
   Alexa's own device list into HA — a device present there but **not** on the bridge means the
   assistant is controlling something else: a **name collision**, not a bridge failure. Deleting it
   in the assistant's app makes the imported entity disappear (that disappearance is the
   confirmation).
5. **Name exposed entities uniquely** and prefer the exact name in the phrase — two devices answering
   to "the lamp" is the usual cause of intermittent voice control.

## Known assistant limits

- **Media players are the weak spot.** The bridge maps a `media_player` to a Matter *Speaker*
  (volume + playback), and Alexa supports **no media-player category at all**, so it degrades to a
  plain on/off device and volume never appears. Two options: change that entity's device type in the
  add-on's UI (e.g. to a plug / light-bearing type), or expose a **helper** the assistant does
  support — a `fan` or a dimmable `light` whose percentage/brightness is bound to the HA attribute.
- Covers, lights, plugs, buttons, sensors, locks, thermostats, fans and vacuums are all supported
  categories.

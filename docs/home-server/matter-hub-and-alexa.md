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
4. If the *bridge itself* shows up twice in the assistant (seen after a factory-reset or a re-created
   bridge while the old pairing still existed), delete the stale bridge in the assistant and pair
   again. Duplicated **accessories** are the other half of that same symptom.

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
6. **Rooms are always assigned by hand.** The bridge *does* publish each entity's Home Assistant area
   (as a Matter `FixedLabel` `room`), but **no major controller reads it** — Google Home, Apple Home
   and Alexa all ignore it, so every accessory must be put in a room in the assistant's app itself,
   after pairing. That is also why a re-import leaves the accessory room-less instead of restoring it.

## A room phrase commands *everything* on/off in that room

"Turn on/off the light in the <room>" is not a lights-only command. The assistant applies the verb to
**every on/off accessory assigned to that room in its own app** — whatever the accessory's category.
Measured on a live setup: a single *"turn on the light in the salon"* produced five commands inside
one second.

```
light.<salon_light>    -> light.turn_on      (wanted)
script.<air_quality>   -> script.turn_on     (fired a spoken notification on the Echo)
remote.<tv>_onoff      -> remote.turn_on     (switched the TV on)
script.<clean_salon>   -> script.turn_on     (started a robot-vacuum cleaning run)
light.<led_strip>      -> light.turn_on      (wanted)
```

The unintended ones were a **script** and a **remote** that had been exposed and landed in the same
room. The pattern is assistant-side, not invented by the bridge: "turn on the living-room light
powers on the whole living-room group" is a long-standing Alexa user report.

- **Room membership is functional, not cosmetic.** Keep exposed scripts, remotes, media players and
  the robot vacuum **out of** any room you address with a light phrase — set those devices to *no
  room* (or a dedicated "commands" room) in the assistant's app. They still work when you say their
  name.
- Only what you actually want switched belongs in the room: bulbs, strips, plugs.
- Diagnose it the same way: one spoken phrase shows up in the bridge log as several invokes within a
  second, and each line names the entity it touched.

## Scripts and scenes are *momentary* — and can wedge the assistant

A `script`, `scene`, `automation` or `input_button` has no real Matter equivalent, so the bridge
publishes it as an on/off accessory that reports **on**, then resets to **off** about a second later.

- Voice control of them is legitimate (one phrase = one whole routine), but they are exactly the
  accessories a room phrase catches by mistake — see above.
- Some Echo models get stuck on that on/off pair: after running one of these, **Alexa stops
  forwarding commands to the whole bridge** until it is restarted. Commands going dead right after a
  script ran is that bug, not a Matter problem.
- Mitigation, in the bridge add-on's UI: **Entity Mapping → "Do not report the on/off flip after a
  run"** (`disableMomentaryFlip`). The Home Assistant action still runs; the entity just stops
  reporting the flip, so the assistant has nothing to choke on.

## Known assistant limits

- **Media players are the weak spot.** The bridge maps a `media_player` to a Matter *Speaker*
  (volume + playback), and Alexa supports **no media-player category at all**, so it degrades to a
  plain on/off device and volume never appears. Two options: change that entity's device type in the
  add-on's UI (e.g. to a plug / light-bearing type), or expose a **helper** the assistant does
  support — a `fan` or a dimmable `light` whose percentage/brightness is bound to the HA attribute.
- Covers, lights, plugs, buttons, sensors, locks, thermostats, fans and vacuums are all supported
  categories.

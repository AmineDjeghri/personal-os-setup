# Parent configs, child configs and variants

AIOStreams gives you three ways to run more than one setup. This page helps you pick one and explains how a child configuration inherits from its parent.

| You want…                                           | Use          | Why                                                                                     |
|-----------------------------------------------------|--------------|-----------------------------------------------------------------------------------------|
| To share your setup with someone else               | Template     | They import a JSON file and get their own configuration and credentials                 |
| Several configurations that follow one base         | Parent/child | Change the parent once and every child follows; each child keeps its own debrid account |
| One configuration with small per-device differences | Variant      | A few lines of script, a diff preview before you save, no second configuration          |

## 🔗 Template or parent config?

- **Template** — for sharing your setup with others, or when you do not want to maintain the configuration afterwards. You publish a JSON file; anyone can import it and gets their own configuration with their own credentials. Nothing links back to yours and there is nothing to keep in sync.
- **Parent config** — for someone who maintains several configurations. One base config holds everything, the others point at its UUID and inherit it, overriding only the sections you choose; change the base once and they all follow. It stays your setup, with your credentials. You will find it in **Miscellaneous → Parent Config** (Advanced mode).
    - You cannot inherit from a configuration that is itself inheriting another one — a configuration can only inherit from the parent directly.

## 🌱 Setting up a child configuration

If the child must have different settings, import the template first, then point the configuration at its parent, delete the addons you do not want to keep locally, and choose a strategy per section. If the only thing that will differ is your debrid account, do not import the template at all: create the configuration and point it at the parent, and everything is inherited.

The per-section strategies decide, section by section, where a child configuration gets its values:

- **Inherit from parent** — use the parent's addons, filters, sorting, formatting… The child's own values for that section are ignored.
- **Extend parent (add mine)** — start from the parent's list and add your own entries. Entries are matched by their internal id, so *your* version of an addon replaces the parent's while the rest keeps inheriting. This is the mode to use when the child only differs by one or two addons.
- **Override with mine** — ignore the parent entirely for that section: the child's own list is used as is.

Two things worth knowing:

- Under *extend*, an addon you add by hand gets a **new internal id** (shown only in a config export), so it is added next to the parent's instead of replacing it — the parent's copy keeps running, even with the same name. An addon that comes from the same template as the parent's keeps the template's id, so the child's copy *replaces* the parent's.
- **Variants are not inherited**: a variant only sees its own configuration's addons, so create it in the configuration you install from.
- Services behave the other way round: a **disabled** service in the child is ignored, so the parent's stays enabled. To switch an inherited debrid account off, use *override* on the Services section.

## 🔀 Turning an addon off for one device (variant)

A variant is a short script that changes your own configuration for one device — no second configuration, no second link to share.

1. Open the configuration and go to **Miscellaneous → Variants** (Advanced mode).
2. Add a variant: give it an **Id** (`no-streamfusion` — lowercase letters, digits, `-` and `_` only) and a **Name** (`No StreamFusion`).
3. In the script box, write the change. To deactivate for example StreamFusion, that is `disable presets[options.name="Streamfusion (Amine)"]`.
4. Save the configuration.

Example — deactivate StreamFusion on a single device:

| Field  | Value                                                  |
|--------|--------------------------------------------------------|
| Id     | `no-streamfusion`                                      |
| Name   | `No StreamFusion`                                      |
| Script | `disable presets[options.name="Streamfusion (Amine)"]` |

To hide every custom addon that needs your own debrid account or key (Lumio, StreamFusion, Statusio) in one go, use a single variant (Id `no-personal-addons`) with one `disable` line per addon. These addons are tied to your own account, so a child configuration or another person cannot reuse them:

```text
disable presets[options.name="Lumio (Amine)"]
disable presets[options.name="Streamfusion (Amine)"]
disable presets[options.name="statusio (Amine)"]
```

`=` is an exact, case-sensitive match on the addon name, so it disables only the addons with that exact name.

💡 **Naming tip.** Give the parent's personal-account addons a recognisable suffix such as `(Amine)`, and keep a child's own copy of the same addon under a different name. The short form `*="Lumio"` is a substring match and would disable both. `=` is case-sensitive: copy the name exactly as it appears in the parent configuration (for example `Streamfusion (Amine)` and `statusio (Amine)` keep their own capitalisation). Addons are merged by their internal `instanceId`, not by name, so a hand-added addon never replaces the inherited one and both stay in the list. Variants are not inherited either: create them in the configuration you install from.

Then go to **Save & Install**, select **No StreamFusion** in the variant list and choose the **path** form. When you copy the manifest URL it must show the selection, as in `…/stremio/<uuid>/<password>/v/no-streamfusion/manifest.json`. Install that URL as the addon on the device that should lose StreamFusion (remove the old one if you replaced it).

The same variant also disables an addon in a **child configuration** that inherited it from a **parent configuration** — the preview may report that the instruction matched nothing, and it still takes effect when you play.

Notes

- Use the **path** form, not `?v=`: clients rebuild the stream requests from the base URL and drop the query string, so only the first request would carry the variant.
- If the variant preview reports *some instructions matched nothing* for an addon that comes from a parent configuration, that is normal — the preview only sees your own configuration, while the script is applied to the merged one when you play.
- Select **Base config** on the Save & Install page to keep installing the unchanged configuration.

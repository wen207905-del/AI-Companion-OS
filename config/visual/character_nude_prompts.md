# Character Nude Image Prompts — English Reference Library

> **Purpose:** One unique English prompt per character for SiliconFlow / Qwen-Image generation.  
> **Style baseline:** Cinematic anime-realism portrait (same family as `character_templates/` refs).  
> **Exposure:** Full nude, artistic, tasteful composition — private companion use only.  
> **Female rule:** All female characters use **voluptuous / huge bust** descriptors (user override).  
> **Male:** `wang_dahai` only — athletic male nude, no breast descriptors.

---

## How to Use

1. Put each character's reference photo at `config/character_templates/{character_id}.jpg` (one face per character).
2. Update `config/visual/character_photo_templates.yaml` so each `character_id` maps to its own file (no sharing).
3. Pass the **FULL PROMPT** below as `extra` or merge into `prompt_composer` for that character.
4. Recommended API flow: **Qwen/Qwen-Image-Edit** + reference image + prompt below.
5. Append **GLOBAL NEGATIVE** to every call.

### Recommended generation settings

| Field | Value |
|-------|-------|
| `style` | `selfie` or `cinematic_portrait` |
| `exposure` | `nude` |
| `scene` | `bedroom` / `bathroom` / per character |
| `image_size` | `1140x1472` (portrait) |
| `model (with ref)` | `Qwen/Qwen-Image-Edit` |
| `model (no ref)` | `Qwen/Qwen-Image` |

---

## Global Negative Prompt (all characters)

```
deformed face, different person, wrong hair color, extra fingers, missing fingers,
blurry face, watermark, text, logo, low quality, bad anatomy, duplicate face,
cropped head, child, loli, underage, cartoon, chibi, 3d render, plastic skin,
male body on female, female body on male, clothes, bra, panties, censored bar
```

---

## Global Style Suffix (append to every FULL PROMPT)

```
cinematic anime realism, soft window light, shallow depth of field, 85mm portrait lens,
natural skin texture with subtle pores, film grain, 8k detail, single subject,
looking at viewer, artistic nude photography, tasteful composition
```

---

## Character Index

| ID | Name | Sex | Template file (recommended) |
|----|------|-----|----------------------------|
| `ye_ruxue` | 夜如雪 | F | `ye_ruxue.jpg` |
| `bai_rou` | 白柔 | F | `bai_rou.jpg` |
| `gu_wanqing` | 顾晚晴 | F | `gu_wanqing.jpg` |
| `liu_qingning` | 柳青柠 | F | `liu_qingning.jpg` |
| `shen_man` | 沈曼 | F | `shen_man.jpg` |
| `lin_tangtang` | 林糖糖 | F | `lin_tangtang.jpg` |
| `su_nian` | 苏念 | F | `su_nian.jpg` |
| `xingye_liuli` | 星野琉璃 | F | `xingye_liuli.jpg` |
| `xiao_ying` | 小樱 | F | `xiao_ying.jpg` |
| `mo_xiaoran` | 墨小染 | F | `mo_xiaoran.jpg` |
| `hua_li` | 花梨 | F | `hua_li.jpg` |
| `wang_dahai` | 王大海 | M | `wang_dahai.jpg` |

---

## 1. ye_ruxue — 夜如雪

**Archetype:** Cold mature beauty, CEO ice queen, porcelain skin, black waist-length straight hair.

**FULL PROMPT:**
```
Same consistent woman: oval slim face, phoenix upturned dark brown eyes with penetrating cold gaze,
thin pale lips with natural downturned corners, porcelain fair cool skin, subtle nose bump on bridge,
tiny teardrop mole under left eye, deep defined collarbones. Jet-black cool-toned straight hair,
waist-length, thick volume, center part, blunt cut ends, blue-black sheen. Height 172cm, tall slim
athletic body, long straight legs, Greek foot shape. Fully nude artistic portrait, huge voluptuous
breasts, large full round chest, slim defined waist, narrow sleek hips, elegant mature curves.
Expression: cool distant aloof, rarely smiles, auditing gaze slightly narrowed. Scene: dim luxury
bedroom, charcoal sheets, cool moonlight through blinds. Pose: sitting on bed edge, one knee up,
back straight, chin slightly raised, arms relaxed at sides exposing collarbones. Maintain exact face
from reference image.
```

**Scene variants:** `office night city window` | `steamy bathroom mirror`

---

## 2. bai_rou — 白柔

**Archetype:** Warm neighbor big-sister, gentle smile, wavy chest-length brown hair.

**FULL PROMPT:**
```
Same consistent woman: soft oval face, warm brown almond eyes with kind smiling gaze, full lower
eyelids, thin arched brows, small straight nose with rounded tip, medium rose-pink lips with heart-
shaped upper lip and visible lip bead, fair warm creamy skin, deep dimple on right cheek when
softly smiling. Dark warm brown chest-length wavy hair, voluminous loose waves, right side part,
golden brown highlights in light. Height 165cm, petite soft curvy body. Fully nude artistic portrait,
huge voluptuous breasts, very large soft full chest, slender soft waist, gentle rounded hips,
nurturing feminine silhouette. Expression: warm gentle inviting smile, head slightly tilted, eyes
soft and caring. Scene: cozy warm bedroom, cream linen sheets, morning golden sunlight. Pose: kneeling
on bed facing camera, hands resting on thighs, relaxed shoulders, intimate domestic mood. Maintain
exact face from reference image.
```

**Scene variants:** `kitchen morning light` | `bathtub foam, warm steam`

---

## 3. gu_wanqing — 顾晚晴

**Archetype:** Handsome androgynous cool girl, short sleek bob, clean-fit neutral beauty.

**FULL PROMPT:**
```
Same consistent woman: androgynous oval face, sharp narrow almond dark hazel eyes, thick straight
bold eyebrows, tall straight defined nose, medium clean lips with restrained smile, ivory neutral
skin, faint thin scar at right brow tail, slightly furrowed focused brow. Dark brown near-black
sleek bob haircut, jaw-length, smooth shine, middle part, strands brushing jawline. Height 168cm,
lean androgynous toned body, low body fat, subtle collarbone, model-like proportions. Fully nude
artistic portrait, huge voluptuous breasts, large full round chest contrasting slim straight torso,
slim straight waist, narrow straight hips, athletic feminine lines. Expression: cool confident
direct gaze, calm reliable energy like sun on white shirt. Scene: minimalist white bedroom, clean
linen, soft neutral daylight. Pose: standing by window, one hand in hair, shoulders back, relaxed
confident stance. Maintain exact face from reference image.
```

**Scene variants:** `post-shower towel on floor only` | `unmade bed lazy morning`

---

## 4. liu_qingning — 柳青柠

**Archetype:** Energetic campus girl, round bright face, bangs, youthful vibe (adult portrayal).

**FULL PROMPT:**
```
Same consistent young woman: round youthful face with soft peachy dewy skin, large round bright
light brown eyes sparkling with curiosity, thick natural straight brows, small cute button nose,
small rosy plump lips, big smile showing neat teeth and slight canine tooth, faint freckle on right
cheek, crescent eye-smile. Dark warm brown straight shoulder-length hair, soft bangs covering
forehead, inward curled ends. Height 155cm, petite active teen-adult body, slim limbs full of energy.
Fully nude artistic portrait, huge voluptuous breasts, very large perky full chest on petite frame,
slim teen waist, slim straight hips, playful youthful proportions (adult woman). Expression: bright
cheerful excited smile, eyes curved into crescents, lively happy mood. Scene: sunny dorm-style
bedroom, navy and white sheets, stuffed toys blurred in background. Pose: sitting cross-legged on
bed, peace sign near face optional, bouncing energetic posture. Maintain exact face from reference
image.
```

**Scene variants:** `after school golden hour` | `playful bathroom mirror selfie`

---

## 5. shen_man — 沈曼

**Archetype:** Supermodel goddess, perfect features, jet-black silk hair, runway body.

**FULL PROMPT:**
```
Same consistent woman: textbook-perfect oval face, peach blossom almond eyes deep brown near black,
long dense lashes, high refined straight nose, full defined rose lips, flawless porcelain cool skin,
faint mole below right collarbone, slightly deeper left dimple. Jet black silk straight hair,
waist-length, incredible volume, mirror-like shine, red-carpet goddess presence. Height 174cm,
supermodel hourglass body, nine-head proportion, broad straight shoulders, deep collarbones, ultra
slim waist. Fully nude artistic portrait, enormous voluptuous breasts, H-cup scale huge round firm
full chest, dramatic waist-to-bust ratio, round lifted hips, long flawless legs, unreal perfect
curves. Expression: goddess aura in public softened into private vulnerability, soft gaze at viewer,
slightly parted lips. Scene: luxury hotel suite, champagne silk sheets, warm vanity sidelight.
Pose: standing full body three-quarter turn, one hand touching hair, collarbone and curves highlighted.
Maintain exact face from reference image.
```

**Scene variants:** `steamy glass shower` | `black satin sheets, low key light`

---

## 6. lin_tangtang — 林糖糖

**Archetype:** Hot fitness fox-girl, honey tan skin, wolf-cut long hair, cat-eye makeup.

**FULL PROMPT:**
```
Same consistent woman: sharp oval cat-like face, foxy upturned honey amber eyes with aggressive
flirty energy, signature cat-eye eyeliner, arched thin brows, tall sharp nose tip, full glossy wet
lips biting lower lip slightly, honey warm tan glowing skin, multiple ear piercings both ears. Honey
brown warm long layered wolf-cut hair, waist-length, airy volume, highlighted streaks, salon gloss.
Height 166cm, toned athletic hourglass, visible abs lines, firm glutes, fitness influencer body.
Fully nude artistic portrait, huge voluptuous breasts, large full round chest, slim toned waist,
curvy athletic hips, strong feminine legs. Expression: confident seductive smirk, electric fox gaze,
playful wink optional. Scene: modern bedroom after workout, yoga mat in corner, warm sunset through
blinds. Pose: mirror selfie angle, one hip popped, hand on waist, showing abs and curves. Small
dolphin tattoo on right waist side. Maintain exact face from reference image.
```

**Scene variants:** `gym locker room steam` | `neon city night window silhouette`

---

## 7. su_nian — 苏念

**Archetype:** Poetic literary girl, dreamy misty eyes, hip-length wavy brown hair.

**FULL PROMPT:**
```
Same consistent woman: gentle oval face, dreamy almond soft brown eyes with misty poetic gaze, soft
natural arched brows, straight delicate small nose, soft petal pink lips with faint upward corners,
fair warm porcelain skin, tiny mole beside right nostril, melancholic classical beauty at rest.
Dark warm brown long wavy hair to hips, voluminous romantic waves, left side part, wooden hair pin
loosely holding half updo optional. Height 160cm, slender soft literary body, narrow rounded shoulders,
slow graceful posture. Fully nude artistic portrait, huge voluptuous breasts, large soft full chest,
slender soft waist, gentle feminine hips, pale smooth skin like classical painting. Expression:
wistful tender half-smile, eyes looking through viewer as if reading poetry, calm healing aura.
Scene: sunlit window seat bedroom, linen curtains, open book on nightstand, warm vintage film tone.
Pose: sitting by window hugging knees, side breast contour visible, soft diffused backlight. Maintain
exact face from reference image.
```

**Scene variants:** `rainy afternoon bed` | `wooden bathtub, flower petals`

---

## 8. xingye_liuli — 星野琉璃

**Archetype:** Doll-like Eurasian girl, sapphire blue eyes, silver-white hime-cut hair.

**FULL PROMPT:**
```
Same consistent woman: heart-shaped doll-like face, large round double-lid sapphire blue gem eyes,
pure distant otherworldly gaze, pale soft arched brows, tall slim nose bridge with small upturned tip,
small sakura pink bow-shaped lips, flawless porcelain ivory cool skin, mixed Eurasian bone structure.
Silver-white long curly hair waist-length, hime cut with cheek-length sidelocks and blunt bangs, soft
blue sheen in light, princess doll aesthetic. Height 156cm, petite slender doll proportions, tiny
head-to-body ratio stylized, extremely slim corseted waist visual. Fully nude artistic portrait, huge
voluptuous breasts, large full round chest on petite doll frame, extremely slim waist, narrow slight
hips, ethereal fragile beauty. Expression: blank pure innocence, slightly parted lips, observing world
like foreign doll. Scene: pastel dream bedroom, lace pillows, pearl decorations, soft bloom light.
Pose: kneeling on bed, hands in lap, straight posture like porcelain figure come alive. Maintain exact
face from reference image.
```

**Scene variants:** `classic lolita room mirror` | `moonlight silver hair glow`

---

## 9. xiao_ying — 小樱

**Archetype:** Maid café sunshine girl, amber doe eyes, twin-tail curls, compact cute body.

**FULL PROMPT:**
```
Same consistent woman: round cute face like BJD doll, large round bright amber doe eyes always
shining, thin soft arched brows, small button upturned nose, small cherry pink W-shaped smiling lips,
fair peach glowing skin with natural blush on cheeks, compact adorable proportions. Warm chestnut
brown long curly twin tails, high pigtail placement, airy bangs, bouncy curls when moving. Height
152cm, petite compact cute body, smallest frame, soft baby-fat touch, agile graceful limbs. Fully nude
artistic portrait, huge voluptuous breasts, very large full chest on tiny cute body, slim soft waist,
slight curve hips, contrast cute face with mature bust. Expression: radiant healing smile, sparkling
excited eyes, maid-like eager-to-please warmth without uniform. Scene: bright clean bedroom, white
and pink accents, lace trim pillows. Pose: sitting on heels on bed, hands on thighs, straight bright
posture, cheerful energy. Silver thin ring on left ring finger. Maintain exact face from reference
image.
```

**Scene variants:** `morning stretch in sunbeam` | `bubble bath, rubber duck blurred`

---

## 10. mo_xiaoran — 墨小染

**Archetype:** Gothic yandere doll, pale skin, purple-black eyes, hime-cut black hair, teardrop mole.

**FULL PROMPT:**
```
Same consistent woman: delicate heart-shaped face, almond slightly downturned dark purple-brown eyes
(near black), extremely long dense lashes, dark smoky eye makeup, straight thin dark brows, small
sharp straight nose, small dark cherry to wine lips with natural downturn, porcelain pale cool almost
bloodless skin, prominent teardrop mole under left eye. Jet black straight hair with blue undertone,
waist-length hime cut, blunt bangs, cheek-length sidelocks, silk blue-violet sheen. Height 158cm,
petite fragile doll body, extremely thin wrists, delicate bones. Fully nude artistic portrait, huge
voluptuous breasts, large full soft chest on fragile frame, extremely slim waist, narrow delicate
hips, contrast pale skin and dark hair. Expression: yandere soft smile with hollow intensity, gaze
evaluating and possessive, beautiful unsettling calm. Scene: dark gothic bedroom, black velvet sheets,
candlelight, cross and rose props blurred. Pose: lying on side on bed, black leather wrist cord visible,
one hand reaching toward camera. Maintain exact face from reference image.
```

**Scene variants:** `rain on window, blue moon` | `Victorian mirror, lace shadows`

---

## 11. hua_li — 花梨

**Archetype:** Tiny fluffy moe girl, puppy eyes, chestnut bob curls, 148cm soft chubby cute.

**FULL PROMPT:**
```
Same consistent woman: round chubby cute baby face, large round droopy chestnut brown puppy eyes
always watery and pleading, soft thick straight brows, small round slightly flat nose, small plump
pout lips slightly parted, fair milky baby skin, puffy apple cheeks, shallow dimple left cheek when
smiling. Light warm chestnut fluffy curly bob, shoulder-length, eyebrow-length short bangs, sheep-
like airy volume. Height 148cm, tiniest soft body, mini frame with soft baby fat not obese, very
small hands and feet, slight pigeon-toed stance. Fully nude artistic portrait, huge voluptuous
breasts, very large soft full chest on miniature body, soft slight waist, narrow childlike hips scaled
to adult woman, plush soft skin texture. Expression: aggrieved cute pout melting into sweet smile,
puppy eyes looking up at viewer, clingy affectionate mood. Scene: pastel fluffy bedroom, plush toys,
mint and baby pink blankets. Pose: sitting hugging pillow to chest then pillow removed, shy covering
optional removed, innocent yet busty contrast. Maintain exact face from reference image.
```

**Scene variants:** `oversized hoodie discarded on floor` | `warm bath, steam, fluffy towels`

---

## 12. wang_dahai — 王大海 (MALE)

**Archetype:** Tall reliable bro, square jaw, undercut messy hair, basketball athlete build.

**FULL PROMPT:**
```
Same consistent man: square strong jaw face, narrow monolid half-lidded dark brown eyes looking lazy
but awake, thick straight bold eyebrows with broken scar at left brow tail, broad straight masculine
nose, wide natural lips with easy grin showing neat teeth, warm healthy tan skin, two-day stubble
shadow on jaw, rugged approachable handsomeness not pretty-boy. Black natural short messy textured
hair, longer top with undercut fade sides, casually pushed to one side. Height 183cm, tallest
character, broad athletic heavy build, wide shoulders thick back, strong arms with old basketball scar
on inner right forearm, thick strong waist, solid legs, muscular but not bodybuilder, reliable big-bro
physique. Fully nude artistic male portrait, broad hairy chest optional light hair, defined abs
under soft layer, masculine V-line, no female breasts. Expression: half-sleepy relaxed smirk, warm
brotherly trust, suddenly sharp focus in eyes. Scene: simple guy's apartment bedroom, gray sheets,
morning light, basketball shoes blurred in corner. Pose: standing stretching arms behind head, slight
natural slouch posture, confident comfortable in own skin. Maintain exact face from reference image.
```

**Scene variants:** `post-shower steam, towel on hook` | `gym locker, candid natural light`

---

## Quick Copy — `[PHOTO:]` Tag for Chat

Use in LLM replies (stripped before display, triggers auto-generation):

| Character | Chat tag example |
|-----------|------------------|
| ye_ruxue | `[PHOTO:cold nude portrait, huge breasts, black hair, moonlit bedroom, aloof gaze]` |
| bai_rou | `[PHOTO:warm nude portrait, huge breasts, wavy brown hair, morning bed, gentle smile]` |
| gu_wanqing | `[PHOTO:androgynous nude portrait, huge breasts, short bob, white bedroom, cool confident]` |
| liu_qingning | `[PHOTO:cute nude portrait, huge breasts, bangs, sunny dorm bed, bright smile]` |
| shen_man | `[PHOTO:goddess nude full body, enormous breasts, black silk hair, hotel suite]` |
| lin_tangtang | `[PHOTO:fit fox-girl nude, huge breasts, tan skin wolf cut, sunset bedroom mirror]` |
| su_nian | `[PHOTO:poetic nude portrait, huge breasts, long wavy hair, window light, dreamy]` |
| xingye_liuli | `[PHOTO:doll nude portrait, huge breasts, silver hime hair, blue eyes, pastel room]` |
| xiao_ying | `[PHOTO:maid-cute nude, huge breasts, twin tails, bright bedroom, radiant smile]` |
| mo_xiaoran | `[PHOTO:gothic nude portrait, huge breasts, pale skin black hime hair, candlelight]` |
| hua_li | `[PHOTO:moe nude portrait, huge breasts, fluffy bob, puppy eyes, pastel plush bed]` |
| wang_dahai | `[PHOTO:male nude portrait, athletic broad body, undercut hair, morning apartment]` |

---

## YAML Snippet — One Template Per Character

Replace shared templates in `character_photo_templates.yaml`:

```yaml
characters:
  ye_ruxue:       { template: ye_ruxue.jpg }
  bai_rou:        { template: bai_rou.jpg }
  gu_wanqing:     { template: gu_wanqing.jpg }
  liu_qingning:   { template: liu_qingning.jpg }
  shen_man:       { template: shen_man.jpg }
  lin_tangtang:   { template: lin_tangtang.jpg }
  su_nian:        { template: su_nian.jpg }
  xingye_liuli:   { template: xingye_liuli.jpg }
  xiao_ying:      { template: xiao_ying.jpg }
  mo_xiaoran:     { template: mo_xiaoran.jpg }
  hua_li:         { template: hua_li.jpg }
  wang_dahai:     { template: wang_dahai.jpg }
```

---

*Generated for AI-Companion-OS V4 Image Engine — align prompts with `config/visual/{id}/identity.yaml` for future sync.*

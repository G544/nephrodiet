"""General (non-personalized) dietary guidance for CKD stage 4, pre-dialysis.

The app currently has no per-patient CKD-stage field or doctor-specified potassium/
phosphorus limits (only salt_limit_g/protein_limit_g are doctor inputs, see
ProfileInput). When the treating nephrologist hasn't given exact numbers, these
constants are the fallback: commonly cited renal-diet targets for stage 4 CKD
(pre-dialysis, not yet on a potassium/phosphate binder regimen). They are a
reasonable *default*, not a substitute for the doctor's own numbers — if the
doctor ever specifies exact potassium/phosphorus limits, wire them into
ProfileInput the same way salt/protein already are, instead of only editing here.

Sources these are broadly consistent with: NKF/KDOQI patient education materials
and standard renal-diet references. Adjust if the doctor provides patient-specific
numbers.
"""

# mg/day. Typical restriction once potassium needs limiting in stage 4 CKD.
POTASSIUM_LIMIT_MG_PER_DAY = 2400.0

# mg/day. Typical restriction for stage 4 CKD to slow secondary hyperparathyroidism.
PHOSPHORUS_LIMIT_MG_PER_DAY = 900.0

# Ingredients to avoid or use only in small, deliberate amounts because they are
# unusually concentrated sources of potassium and/or phosphorus — grouped for use
# inside LLM prompts, not enforced in code (no per-ingredient nutrient database exists).
HIGH_POTASSIUM_INGREDIENTS_RU = (
    "бананы, апельсины и апельсиновый сок, дыня, курага и другие сухофрукты, авокадо, "
    "томаты и томатная паста/соус в большом количестве, картофель без вымачивания, "
    "шпинат, свёкла, бобовые (фасоль, чечевица, нут), орехи и семечки, шоколад/какао, "
    "заменители соли на основе хлорида калия"
)
HIGH_PHOSPHORUS_INGREDIENTS_RU = (
    "молочные продукты в большом количестве (особенно твёрдый сыр), орехи и семечки, "
    "бобовые, отруби и цельнозерновые продукты в большом количестве, желток яйца в "
    "большом количестве, переработанное мясо и продукты с фосфатными добавками "
    "(колбасы, готовые полуфабрикаты, плавленый сыр, газированные напитки на основе колы)"
)

# Grouped separately because grибы/mushrooms are a specific ingredient the user
# flagged directly — moderately high in both potassium and phosphorus.
CAUTION_INGREDIENTS_RU = "грибы (в т.ч. шампиньоны)"

POTATO_PREP_INSTRUCTION_RU = (
    "Картофель и другие крахмалистые корнеплоды (например, топинамбур) обязательно "
    "готовь с вымачиванием для снижения калия: очисти, нарежь тонкими ломтиками или "
    "мелкими кубиками, замочи в большом объёме воды минимум на 2 часа (лучше на ночь, "
    "сменив воду один раз), затем отвари в свежей воде и эту воду тоже слей — не "
    "используй воду от вымачивания или варки картофеля для соуса/супа."
)

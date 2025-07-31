import sys, types


def _stub(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


# Список лёгких зависимостей, которые могут отсутствовать в окружении CI/песочницы
missing = [
    "aiogram",
    "aiogram.fsm",
    "aiogram.fsm.context",
    "aiogram.fsm.state",
    "aiogram.types",
    "structlog",
    "pydantic",
    "pydantic_settings",
    "fitz",
    "docx",
    "aioresponses",
    "pytesseract",
    "celery",
    "aiogram.utils",
    "aiogram.utils.keyboard",
    "redis",
    "redis.asyncio",
    "aiohttp",
    "aiofiles",
    "Levenshtein",
    "pdfplumber",
]

for pkg in missing:
    if pkg not in sys.modules:
        # Создаём пакет и вложенные подмодули
        parts = pkg.split(".")
        for i in range(1, len(parts) + 1):
            subname = ".".join(parts[:i])
            if subname not in sys.modules:
                mod = _stub(subname)
                if subname == "yadisk":

                    class _Y(_Dummy):
                        def __init__(self, *a, **kw):
                            pass

                    mod.YaDisk = _Y

# stub pdfplumber extraction
if "pdfplumber" in sys.modules:
    pdp = sys.modules["pdfplumber"]

    class _PDF:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def pages(self):
            return []

    pdp.open = lambda *a, **kw: _PDF()

# если _Dummy ещё не определён (используется ниже)
if "_Dummy" not in globals():

    class _Dummy:  # noqa: D401
        def __getattr__(self, _):
            return self


# redis.asyncio alias to dummy Redis
if "redis.asyncio" in sys.modules:
    rmod = sys.modules["redis.asyncio"]

    class _Redis(_Dummy):
        async def get(self, *a, **kw):
            return None

        async def set(self, *a, **kw):
            return None

        async def zincrby(self, *a, **kw):
            return None

        async def zadd(self, *a, **kw):
            return None

        async def expire(self, *a, **kw):
            return None

        async def smembers(self, *a, **kw):
            return set()

        async def sadd(self, *a, **kw):
            return None

        async def srem(self, *a, **kw):
            return None

    rmod.Redis = _Redis

    def from_url(url):
        return _Redis()

    rmod.from_url = from_url

# aiohttp minimal
if "aiohttp" in sys.modules:
    ahttp = sys.modules["aiohttp"]

    class _Resp(_Dummy):
        status = 200

        async def text(self):
            return ""

    class _Session(_Dummy):
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, *a, **kw):
            return _Resp()

    ahttp.ClientSession = lambda *a, **kw: _Session()
    ahttp.ClientTimeout = _Dummy

# aiofiles
if "aiofiles" in sys.modules:
    af = sys.modules["aiofiles"]

    async def open(*a, **kw):
        class _F(_Dummy):
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def read(self):
                return ""

        return _F()

    af.open = open

# Levenshtein
if "Levenshtein" in sys.modules:
    lev = sys.modules["Levenshtein"]

    def ratio(a, b):
        return 0.0

    lev.ratio = ratio

# ensure yadisk.YaDisk attribute
if "yadisk" in sys.modules:
    y = sys.modules["yadisk"]

    class _Y(_Dummy):
        def __init__(self, *a, **kw):
            pass

    y.YaDisk = _Y

# Минимальная реализация нужных классов для aiogram
if "aiogram" in sys.modules:
    import types as _t

    aiogram = sys.modules["aiogram"]

    class _Dummy:  # pylint: disable=too-few-public-methods
        def __init__(self, *a, **kw):
            pass

        def __call__(self, *a, **kw):
            return self

        def __getattr__(self, _):
            return self

        # поддержка сравнения F.text == ... : возвращаем self для text
        @property
        def text(self):  # noqa: D401
            return self

        def __eq__(self, other):  # noqa: D401
            return False

        # декораторы aiogram
        def message(self, *a, **kw):
            def decorator(func):
                return func

            return decorator

        def callback_query(self, *a, **kw):
            def decorator(func):
                return func

            return decorator

    for name in [
        "Router",
        "Bot",
        "Message",
        "CallbackQuery",
        "InlineKeyboardButton",
        "KeyboardButton",
        "InlineKeyboardMarkup",
        "InlineKeyboardBuilder",
    ]:
        setattr(aiogram, name, _Dummy)

    # объект F – экземпляр, а не класс
    aiogram.F = _Dummy()

    # aiogram.filters
    filters_mod = sys.modules.get("aiogram.filters") or _stub("aiogram.filters")
    filters_mod.Command = _Dummy

    sub_names = {
        "aiogram.fsm.context": ["FSMContext"],
        "aiogram.fsm.state": ["State", "StatesGroup"],
        "aiogram.types": [
            "Message",
            "CallbackQuery",
            "InlineKeyboardButton",
            "InlineKeyboardMarkup",
            "KeyboardButton",
            "ReplyKeyboardMarkup",
            "FSInputFile",
        ],
        "aiogram.enums": ["ParseMode"],
        "aiogram.client.default": ["DefaultBotProperties"],
    }

    for mod_name, attrs in sub_names.items():
        mod = sys.modules.get(mod_name) or _stub(mod_name)
        for attr in attrs:
            setattr(mod, attr, _Dummy)

    # aiogram.utils.keyboard
    utils_mod = sys.modules.get("aiogram.utils") or _stub("aiogram.utils")
    kb_mod = sys.modules.get("aiogram.utils.keyboard") or _stub("aiogram.utils.keyboard")

    class _KB(_Dummy):
        def button(self, *a, **kw):
            return None

        def adjust(self, *a, **kw):
            return None

        def as_markup(self):
            return None

    kb_mod.InlineKeyboardBuilder = _KB

# structlog заглушка
if "structlog" in sys.modules:
    sl = sys.modules["structlog"]

    def _get_logger(*a, **kw):
        class _L:  # noqa: D401
            def __getattr__(self, _):
                return lambda *a, **kw: None

        return _L()

    sl.get_logger = _get_logger

# pydantic заглушка
if "pydantic" in sys.modules:
    import types as _t2

    pd = sys.modules["pydantic"]

    def _field(default=None, **kwargs):  # noqa: D401
        return default

    class _BaseSettings:  # noqa: D401
        def __init__(self, *a, **kw):
            pass

    pd.Field = _field
    pd.BaseSettings = _BaseSettings

    # pydantic_settings compatibility
    ps_name = "pydantic_settings"
    if ps_name not in sys.modules:
        sys.modules[ps_name] = _t2.ModuleType(ps_name)
    ps = sys.modules[ps_name]
    ps.BaseSettings = _BaseSettings

    def _settings_config_dict(**kw):
        return dict

    ps.SettingsConfigDict = _settings_config_dict

# aioresponses заглушка (для простых проверок количества запросов)
if "aioresponses" in sys.modules:
    ar = sys.modules["aioresponses"]

    class _AioResp(dict):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def get(self, url, **kw):
            self[url] = kw

        @property
        def requests(self):
            return self

    ar.aioresponses = lambda *a, **kw: _AioResp()

# ocrmypdf заглушка
if "ocrmypdf" not in sys.modules:
    _stub("ocrmypdf")

# yadisk заглушка
if "yadisk" not in sys.modules:
    _stub("yadisk")
    _stub("yadisk.exceptions")
    import types as _t3

    yex = sys.modules["yadisk.exceptions"]

    class _YE(Exception):
        pass

    yex.YaDiskError = _YE

# гарантия атрибута YaDisk на объекте yadisk
if "yadisk" in sys.modules:
    yd = sys.modules["yadisk"]
    if not hasattr(yd, "YaDisk"):

        class _Ya(_Dummy):
            def __init__(self, *a, **kw):
                pass

        yd.YaDisk = _Ya

# ensure PIL.Image attribute exists
if "PIL" in sys.modules:
    pil = sys.modules["PIL"]
    if not hasattr(pil, "Image"):
        pil.Image = _Dummy
else:
    pil = _stub("PIL")
    pil.Image = _Dummy

# ensure Celery attribute exists after stub
if "celery" in sys.modules:
    cel = sys.modules["celery"]
    if not hasattr(cel, "Celery"):

        class _Cel(_Dummy):
            def task(self, *a, **kw):
                def deco(f):
                    return f

                return deco

            def send_task(self, *a, **kw):
                pass

        cel.Celery = _Cel

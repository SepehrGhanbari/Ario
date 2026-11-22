# R63 G7 — اتصال محدودِ نامزد seq4 به امضای بومی CNG با کلید ساختگی

**تاریخ:** 2026-11-22  
**شاخه:** `research/r63-g7-seq4-native-cng-integration-20261122`  
**حکم:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO`

## نتیجهٔ اصلی — دیگر نیازی به بازآزمون بی‌پایان هش نداریم

تعداد زیادی از قطعات جداگانهٔ R62/R63 قبلاً آزمایش شده‌اند: صحت زنجیرهٔ V1/V2، DACL حساب نویسنده و خواننده، هویت واقعی اتصال Named Pipe در G4، حداقل تاریخی seq3 در G5 و امتداد seq4 در G6، و یک راه مستقل برای تولید/بازبینی امضای **واقعیِ محاسباتی** `NCryptSignHash` با **کلید ساختگی موقت**. این‌ها به‌تنهایی هنوز امضاکنندهٔ مستقل آریو نیستند.

G7 قطعات فعلی را در یک مسیر محدودتر به هم پیوند می‌زند: **از بایت‌های منجمد G4 و سابقهٔ ثابت seq3 → نامزد بررسی‌شدهٔ seq4 → امضای native موقت → راستی‌آزمایی فقط‌عمومی → بازخوانی دوبارهٔ داده‌های ورودی.**

## شواهد واقعی CI

[اجرای نهایی موفق GitHub Actions #45025510361](https://github.com/SepehrGhanbari/Ario/actions/runs/45025510361): سه job با نتیجهٔ success:

- `source-and-negative-controls / Windows Server 2022`: **22/22 G7** و **28/28 G6**؛
- `source-and-negative-controls / Ubuntu 24.04`: **22/22 G7** و **28/28 G6**؛
- `native-disposable-signature-integration / Windows Server 2022`: native `NCryptSignHash` **enter=1، return=1**، صحت امضای ECDSA P-256 در مسیر تأییدکنندهٔ عمومی PASS، رد امضای دست‌کاری‌شده و hash تغییرکرده PASS، کنترل مجدد داده پس از امضا PASS، جایگزینی بایت V2 پس از امضا `HOLD_CHAIN_INVALID` با exit 2، و حذف کلید ساختگی `DISPOSABLE_KEY_ABSENT_AFTER_DELETE=True`.

شواهد عمومیِ بدون کلید خصوصی: [artifact #14755074415](https://github.com/SepehrGhanbari/Ario/actions/runs/45025510361/artifacts/14755074415) شامل payload، metadata، public-only receipt و **public pin ساختگیِ همان runner**. SHA256 رسید ذخیره‌شده (از لاگ native): `2554cd561645c47c4aab99508772bff7584a45a198d12e772b56cf75894e5ae8`. public pin همین run: `199d397f93ace2cc24bb845077b71acfa9dace0c9ba72f1fa6aa464427e31619`؛ **برای هیچ کلید واقعی یا دستگاه دیگر معتبر نیست**.

در اولین اجرای `#45025413005`، سه مرحلهٔ واقعی امضا/راستی‌آزمایی/تست دست‌کاری در لاگ موفق بودند ولی job به‌خاطر **باقی‌ماندن exit code=2 از کنترل منفی مورد انتظار** با نتیجهٔ قرمز پایان یافت. با افزودن `exit 0` **فقط پس از بررسی صریح تمام شروط مثبت و منفی**، اجرای دوم `#45025510361` سبز شد. کنترل fail-closed تضعیف نشده و اجرای اول همچنان محفوظ است.

## کدام کد

- `g7_native_checkpoint/g7_preflight.py`: هش منجمد ماژول V9 `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`، تطبیق بایت‌های اولیه G4، حداقل تاریخی seq3/head، و **همان یک رویداد** seq4/head=`52e1f33cf8bcf325a2cb817abe16473aa2e6a799fc76406b8cf831b912fd6d8c`. بعد از امضای آزمایشی، payload و metadata با بایت‌های تازهٔ زنجیره دوباره تطبیق می‌شوند. هیچ برداشت مستقیم از Notes آیفون و هیچ ارتقای خودکار حداقل تاریخی وجود ندارد.
- `g7_native_checkpoint/test_g7_preflight.py`: 22 کنترل معتبر/نامجاز، شامل seq2 rollback، seq4 fork، pin پایین‌آمده یا جعلی، دست‌کاری قبل و بعد از امضا، پاک شدن payload و امتناع از بازنویسی شواهد.
- `.github/workflows/r63-g7-seq4-cng-research.yml`: Windows/Linux tests و Windows native key فقط در `RUNNER_TEMP` با `contents:read` و `persist-credentials:false`، با استفاده از اسکریپت **از قبل موجود** `research/r63_v10_native_replay_ci/Invoke-NativePublicReceipt.ps1`. هیچ تغییر در runner host دائمی، لپ‌تاپ امضاکننده، کلید آریو، Rulesets یا main.

## مرز اثبات — کلید شخصی آریو را هنوز فعال نکن

1. **امضای معتبر ریاضی ≠ مجوز استفاده از امضاکنندهٔ آریو.** این کلید ephemeral و self-pinned است و توسط همان مدیر آزمایشگاه ساخته و حذف می‌شود. صدور رسید مجاز R60، دو رأی مستقلِ بنیان‌گذار/آریو، ابطال معتبر و veto در مسیر بومی واقعی **تست نشده‌اند**.
2. کنترل‌های G4 (توکن واقعی pipe)، G6 (حداقل تاریخی) و G7 (امضای native) هر کدام در مراحل/فرایندهای جدا به موفقیت رسیده‌اند؛ **مرز اتمیک بین پذیرش مجوز → ثبت پایدار مصرف → فراخوانی CNG** هنوز در یک signer واقعی یکپارچه نشده. مدیر runner می‌تواند کنترل‌ها را دور بزند.
3. سناریوی مهم «`NCryptSignHash` برمی‌گردد ولی فرایند **قبل از ثبت پایدار رسید** سقوط می‌کند» و مسیرِ تکرار درخواست بدون امضای دوباره **هنوز تحت همان کلید و broker واقعی V9** آزمایش نشده است.
4. حداقل تاریخچهٔ آیفون **همچنان seq=3** است؛ seq4 هنوز یک نامزد تأییدنشده است. حتی رسید امضای جدید CI نه «آخرین وضعیت معتبر» را اثبات می‌کند، نه مالکیت مستقل کلید را، نه جلوگیری در برابر rollback مشترک مدیر.
5. کد اجرای آزمایشی `g7_preflight.py` فقط منبع/معنا را می‌بندد؛ `Invoke-NativePublicReceipt.ps1` اعتبار مجوز صادرکننده را تضمین نمی‌کند. این برای آزمایش CNG کفایت دارد و برای production کافی نیست.

## برای اینکه امضا از چرخهٔ طولانی آزمایش‌های پراکنده خارج شود

**مرحلهٔ واحد بعدی: R63 NATIVE SIGNER END-TO-END، فقط مهمان disposable ویندوز و کلید Software KSP ساختگی.**

- *پیش از CNG:* مجوز ساختگیِ معتبر با مشخصات epoch/nonce/هش شواهد، سهم دو بازیگر انسانیِ بنیان‌گذار و آریو، veto و revocation، درخواست‌کننده با SID واقعی، و وضعیت شاهد پایدار/آخرین pin پذیرش را به **همان broker واقعی** متصل کنید. اجازهٔ عبور از کنترل‌ها با صرف یک برچسب در payload ممنوع.
- *در مرز مصرف:* durable reservation + use-intent مستقل از پاسخ RPC ثبت و با شناسهٔ nonce یکتا شود؛ سپس حساب دقیق `NCryptSignHash enter/return` در همان broker خوانده شود.
- *سه سقوط لازم:* قبل از CNG = 0 sign؛ بعد از CNG و قبل از رسید = `HOLD_UNCERTAIN` و 0 **sign مجدد** برای همان nonce؛ بعد از durable receipt و قبل از ACK = **دقیقاً همان بایت‌های رسید عمومیِ معتبر** و 0 sign مجدد.
- *مرز اعتماد:* شاهد تاریخی Rekor و آیفونِ جدا، **اثبات latest خودکار/متولی مستقلِ امضا نیستند**. هرگونه پیشروی به کلید واقعی یا production منوط به سیاست custody/rotation/recoveryِ مجزا و تصمیم صریح بنیان‌گذار است.

**تصمیم:** `G7_EXACT_SOURCE_BOUND_CNG_SYNTHETIC=PASS`، `G7_PUBLIC_SIGNATURE_VERIFIED=PASS`، `G7_POSTSIGN_TAMPER=HOLD`؛ اما `NATIVE_V9_END_TO_END=NOT_EXECUTED`، `COMPLETE_USE_AND_CUSTODY=NOT_ESTABLISHED`، `INDEPENDENT_LATEST=NOT_ESTABLISHED`، `PRODUCTION=NO_GO`. **لپ‌تاپ و کلیدهای واقعی دست‌نخورده‌اند؛ هیچ مرجی انجام نشده است.**

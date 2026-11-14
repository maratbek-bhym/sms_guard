"""Шаблоны синтетических SMS. {a|b|c} — случайный выбор, <slot> — подстановка.
Каждый шаблон = «семейство» (family) для группового разбиения. Все данные искусственные."""

# (язык, класс, категория) -> список шаблонов. класс: safe / fraud / suspicious
T = {}


def add(lang, cls, cat, *tpls):
    T.setdefault((lang, cls, cat), []).extend(tpls)


# ============================ RU ============================
add("ru", "safe", "chat",
    "{Привет|Здорово|Хай}, <name>! {Ты|Вы} {сегодня|завтра} {придёшь|будешь} на {встречу|тренировку|пары}? Я {буду|приду} к <time> {у входа|возле метро|у кофейни}.",
    "<name>, {напиши|набери} как {освободишься|будешь дома}. {Купить хлеб по пути?|Ужин в семь, не опаздывай.|Я задержусь минут на десять.}")
add("ru", "safe", "family",
    "{Мама|Папа|Бабушка}: {не забудь|помни} {про|что} {день рождения|ужин|поездку} {у тёти|в субботу|на даче}. {Целую!|Позвони вечером.|Люблю.}",
    "<name>, {спасибо за подарок|поздравляю с днём рождения|с праздником}! {Обнимаю|Жду в гости|Увидимся в выходные}.")
add("ru", "safe", "delivery",
    "Ваш заказ №<num> {передан в доставку|отправлен|ожидает в пункте выдачи} и {будет доставлен|прибудет} <date>.{ Отследить: <urlsafe>|}",
    "Курьер {будет у вас|приедет} <date> {с 10 до 14|после 18:00}. {Телефон курьера: <phone>|Оплата уже произведена.}")
add("ru", "safe", "bank_notice",
    "<bank>: {покупка|оплата|списание} <amt> {в магазине|в супермаркете|в кафе} <place>, карта *<card4>. {Доступно|Баланс}: <amt>.",
    "<bank>: {пополнение|перевод} <amt> {на карту *<card4>|от <name>}. {Если это не вы — позвоните по номеру на обратной стороне карты.|}",
    "<bank>: {по вашей просьбе|согласно заявлению} карта *<card4> {заблокирована|временно заблокирована}. {Разблокировать можно в приложении или в отделении.|}")
add("ru", "safe", "otp",
    "{Код подтверждения|Ваш код|Одноразовый код}: <code>. {Никому не сообщайте|Не передавайте} {его|этот код} {никому|третьим лицам}, {даже сотрудникам банка|включая сотрудников <bank>}.",
    "<code> — код для {входа|оплаты <amt>} в <org>. {Действует 5 минут.|Если вы не запрашивали код, проигнорируйте это сообщение.}")
add("ru", "safe", "reminder",
    "{Напоминаем|Напоминание}: {приём у врача|встреча|стоматолог|занятие} <date> в <time>. {Для переноса звоните <phone>|Адрес: <place>}.")
add("ru", "safe", "gov_edu",
    "{Деканат|Университет|Школа №<num>}: {занятия|экзамен|собрание} {перенесены|состоятся} на <date>, <time>. {Аудитория <num>.|}",
    "{ЦОН|Налоговая|Акимат}: {ваши документы готовы|ваша заявка принята|приём по записи}. {Номер заявки <num>.|Подробнее: <urlgov>}",
    "{Налоговая|Акимат}: {штраф|задолженность} <amt> {оплачен|погашен}. Спасибо.")
add("ru", "safe", "ads",
    "<org>: {скидки до 30%|распродажа|новая коллекция} {в магазинах|на сайте|в приложении} {до <date>|только в эти выходные}. {Отписаться: ответьте СТОП|Подробности: <urlsafe>}")
add("ru", "safe", "purchase",
    "{Спасибо за покупку|Чек} в <org>. {Сумма|Итого} <amt>.{ Электронный чек: <urlsafe>|}")
add("ru", "safe", "work",
    "<name>, {отчёт|презентация|договор} {готов|на согласовании}. {Созвон в|Встреча в} <time> {в переговорной|в Zoom}. {Нужны правки до завтра.|}",
    "{Срочно|Важно}: {совещание перенесено на <time>|клиент ждёт ответ до <time>}. {Подтвердите участие.|}")

add("ru", "fraud", "bank_phish",
    "{<bank>|Служба безопасности <bank>}: {в вашем личном кабинете|в вашем профиле} {обнаружена подозрительная активность|выявлен вход с нового устройства}. {Для защиты средств|Чтобы избежать блокировки} {войдите|авторизуйтесь} {на сайте|по ссылке}: <urlphish>",
    "{Уважаемый клиент|Клиент <bank>}, {срок действия вашего пароля истёк|ваши данные устарели}. {Обновите|Подтвердите} {данные|информацию} в {течение 24 часов|ближайшее время}: <urlphish>")
add("ru", "fraud", "cvv_code",
    "{Сотрудник службы безопасности <bank>|Служба безопасности}: {для отмены|для блокировки} {подозрительной операции|списания <amt>} {назовите|продиктуйте|сообщите} {код из SMS|CVV-код|пин-код}.",
    "Вам {позвонят|звонил} {сотрудник|специалист} <bank>. {Сообщите|Продиктуйте} ему {трёхзначный код с обратной стороны карты|код из этого сообщения: <code>} {для сверки данных|для защиты счёта}.")
add("ru", "fraud", "card_block",
    "Ваша карта {заблокирована|ограничена|будет заблокирована}{!|.} {Срочно|Немедленно|Сегодня} {подтвердите данные|разблокируйте карту} {по ссылке|на сайте}: <urlphish>",
    "<bank>: {доступ к карте *<card4> ограничен|операции по карте приостановлены}. {Для снятия ограничений|Чтобы продолжить пользоваться картой} {перейдите|пройдите проверку}: <urlphish>")
add("ru", "fraud", "delivery_customs",
    "Ваша посылка {ожидает|задержана} {на таможне|на складе}. {Оплатите|Необходимо оплатить} {таможенный сбор|доплату за доставку} <amt> {до <date>|в течение 48 часов}: <urlphish>",
    "{Курьер не смог доставить|Не удалось доставить} посылку №<num>. {Уточните адрес|Обновите адрес доставки} {и оплатите хранение <amt>|}: <urlphish>")
add("ru", "fraud", "gov_payment",
    "{Госуслуги|Минфин|Соцфонд}: {вам одобрена|вам положена} {социальная выплата|компенсация|возврат налога} <amt>. {Получите|Оформите} {выплату|средства} {до <date>|в течение 3 дней}: <urlphish>",
    "{Вам начислено пособие|Ваш налоговый вычет одобрен}. {Для зачисления на карту|Чтобы получить деньги} {заполните анкету|укажите реквизиты карты}: <urlphish>")
add("ru", "fraud", "prize",
    "{Поздравляем|Вы счастливый обладатель}! {Вы выиграли|Вам достался} {приз|смартфон|автомобиль|<amt>} в {розыгрыше|акции} <org>. {Заберите|Получите} {приз|выигрыш}: <urlphish>",
    "{Ваш номер выбран|Вы стали победителем} {в лотерее|среди клиентов <org>}! {Для получения подарка|Чтобы забрать выигрыш} {оплатите комиссию <amt>|ответьте на это сообщение|перейдите по ссылке <urlphish>}.")
add("ru", "fraud", "money_transfer",
    "{Добрый день|Здравствуйте}! {Это <name> из <org>|Вам пишет бухгалтерия}. {Ошибочно перевели вам|Перевели вам деньги по ошибке} <amt>, {верните пожалуйста на номер <phone>|пожалуйста, верните на карту ****<card4>}.")
add("ru", "fraud", "relative",
    "{Мама|Бабушка|Пап}, {я попал в аварию|у меня проблемы с полицией|я в больнице}. {Срочно переведи|Нужно срочно <amt>:} {на этот номер <phone>|на карту}, {объясню потом|телефон разбит, пишу с чужого}.",
    "{Привет, это <name>|Это твой сын}, {сменил номер|телефон сломался}. {Скинь|Переведи} <amt> {на карту, потом отдам|срочно, расскажу позже}.")
add("ru", "fraud", "investment",
    "{Инвестиции|Криптовалюта|Торговля на бирже}: {доход|прибыль} {от 30% в неделю|до <amt> в день}! {Гарантия возврата|Без риска}. {Вступай|Присоединяйся} в {чат|Telegram} @<handle>.",
    "{Мой знакомый брокер|Наш аналитик} {поделился|показал} {схемой|стратегией}: {вложил <amt>, получил втрое|забрал за неделю втрое больше}. {Хочешь так же|Напиши}? @<handle>")
add("ru", "fraud", "tech_support",
    "{Поддержка|Техническая поддержка} <org>: {ваш аккаунт|ваше устройство} {взломан|заражён вирусом}. {Установите|Скачайте} {приложение для защиты|программу удалённой помощи} {по ссылке|здесь}: <urlphish>",
    "{Служба поддержки|Специалист}: {мы заметили вирус на вашем телефоне|ваш компьютер заражён}. {Позвоните|Свяжитесь} {по номеру <phone>|в чат @<handle>}, {не выключая устройство|мы поможем}.")
add("ru", "fraud", "debt",
    "{Уведомление|Повестка}: {у вас задолженность|за вами числится долг} <amt> {по кредиту|по налогам|за коммунальные услуги}. {Погасите|Оплатите} {до <date>|сегодня} {во избежание суда|иначе дело передадут приставам}: <urlphish>")
add("ru", "fraud", "account_pwd",
    "{Ваш аккаунт|Ваша учётная запись} <org> {будет удалён|заблокирован} {через 24 часа|сегодня}. {Подтвердите|Сбросьте} {пароль|вход} {здесь|по ссылке}: <urlphish>",
    "{Кто-то пытался войти в ваш аккаунт|Обнаружен вход с нового устройства}. {Если это не вы|Для защиты} {смените пароль|введите логин и пароль}: <urlphish>")
add("ru", "fraud", "fake_job",
    "{Здравствуйте|Добрый день}! {Мы изучили ваше резюме|Приглашаем на удалённую работу}. {Оплата|Доход} <amt> {в день|за смену}, {без опыта|свободный график}. {Задания выполняются в телефоне|Обучение бесплатное}. {Пишите|Напишите} в WhatsApp <phone>.",
    "{Требуются|Набор} {помощники|операторы} {на дому|онлайн}: {лайки|отзывы|заказы}, {оплата сразу|заработок <amt>}. {Начни сегодня|Пиши} @<handle>")
add("ru", "fraud", "bonus_refund",
    "{Вам доступен|Начислен} {бонус|кэшбэк|возврат} <amt> {от <bank>|на карту}. {Активируйте|Заберите} {его|бонус} {до <date>|до конца недели}: <urlphish>",
    "{Вернём деньги|Вам положена компенсация} {за покупку|за услуги связи}. {Укажите номер карты|Оставьте данные карты} {для зачисления|чтобы получить <amt>}: <urlphish>")
add("ru", "fraud", "fear_secrecy",
    "{Это последнее предупреждение|Внимание}. {Ваши данные|Ваши фото} {стали известны|попали в сеть}. {Никому не говорите|Не обращайтесь в полицию}, {иначе|чтобы избежать последствий} {переведите <amt>|свяжитесь со мной @<handle>}.",
    "{Вы подозреваетесь в|На вас поступило заявление о} {мошенничестве|нарушении}. {Немедленно позвоните <phone>|Явка обязательна}. {Разговор строго конфиденциален|Не сообщайте никому}.")
add("ru", "suspicious", "loan_ad",
    "{Выгодное предложение|Только сегодня}! {Займ|Кредит} {до <amt>|без отказа} {за 5 минут|на карту}. {Подробности|Оформить}: <urlsus>")
add("ru", "suspicious", "otp_nowarn", "{Ваш код|Код}: <code>. {Введите его|Используйте} на сайте <org>.")
add("ru", "suspicious", "unknown_link", "{Привет|Здравствуйте}, {это <name>|вы нас не знаете}. {Посмотри|Глянь} {это|вот это}: <urlsus>")

# ============================ KK ============================
add("kk", "safe", "chat",
    "{Сәлем|Қалайсың|Амансың ба}, <name>! {Бүгін|Ертең} <time>-де {кездесеміз бе|кездесейік|жолығамыз ба}? {Мен кітапхана алдында боламын|Кафе жанында күтемін|Жұмыстан кейін хабарласамын}.",
    "<name>, {үйге келгенде|бос болғанда} {хабарла|қоңырау шал}. {Нан алып келе ме?|Кешкі асқа үлгер.|Дүкеннен сүт алып кел.}")
add("kk", "safe", "family",
    "{Анам|Әкем|Әжем}: {туған күнді|кешкі асты|сенбідегі кездесуді} {ұмытпа|есіңде болсын}. {Кешке қоңырау шал.|Аман бол!|Сені сағындық.}",
    "<name>, {сыйлық үшін рахмет|туған күніңмен|мерекең құтты болсын}! {Демалыста кездесеміз|Қонаққа кел}.")
add("kk", "safe", "delivery",
    "Сіздің №<num> тапсырысыңыз {жөнелтілді|жеткізуге берілді|беру пунктіне келді}. {Жеткізу күні|Күтілетін күні}: <date>.{ Бақылау: <urlsafe>|}",
    "Курьер <date> {сағат 10-нан 14-ке дейін|кешкі 18:00-ден кейін} {келеді|жетеді}. {Курьер нөмірі: <phone>|Төлем төленген.}")
add("kk", "safe", "bank_notice",
    "<bank>: <place> {дүкенінде|кафесінде|дәріханасында} <amt> {төлем жасалды|сомасына сатып алу}, карта *<card4>. {Қалдық|Қолжетімді сома}: <amt>.",
    "<bank>: карта *<card4>-ға <amt> {түсті|аударылды}. {Егер бұл сіз болмасаңыз, картаның артындағы нөмірге қоңырау шалыңыз.|}",
    "<bank>: сіздің өтінішіңіз бойынша карта *<card4> {уақытша бұғатталды|бұғатталды}. {Қосымшада немесе бөлімшеде ашуға болады.|}")
add("kk", "safe", "otp",
    "{Растау коды|Сіздің кодыңыз|Бір реттік код}: <code>. {Оны ешкімге айтпаңыз|Кодты ешкімге бермеңіз}, {банк қызметкерлеріне де|тіпті <bank> қызметкеріне де}.",
    "<code> — <org> {жүйесіне кіру|<amt> төлемін растау} коды. {5 минут жарамды.|Егер сіз сұрамасаңыз, бұл хабарламаны елемеңіз.}")
add("kk", "safe", "reminder",
    "{Еске саламыз|Ескертеміз}: <date> сағат <time>-де {дәрігер қабылдауы|кездесу|жаттығу|сабақ}. {Мекенжайы: <place>|Ауыстыру үшін <phone> нөміріне хабарласыңыз}.")
add("kk", "safe", "gov_edu",
    "{Университет|Мектеп №<num>|Деканат}: {сабақ|емтихан|жиналыс} <date> күніне, <time>-ге {ауыстырылды|белгіленді}. {Аудитория <num>.|}",
    "{ХҚКО|Салық комитеті|Әкімдік}: {құжаттарыңыз дайын|өтінішіңіз қабылданды|қабылдау алдын ала жазылу бойынша}. {Өтінім нөмірі <num>.|Толығырақ: <urlgov>}",
    "{Салық комитеті|Әкімдік}: <amt> {айыппұл|берешек} {төленді|өтелді}. Рахмет.")
add("kk", "safe", "ads",
    "<org>: {жеңілдік 30%-ға дейін|жаңа коллекция|сатылым} {дүкендерде|қосымшада|сайтта} <date> дейін. {Бас тарту үшін СТОП деп жауап беріңіз|Толығырақ: <urlsafe>}")
add("kk", "safe", "purchase",
    "<org>-дан {сатып алғаныңыз үшін рахмет|чек}. {Жалпы сома|Сомасы} <amt>.{ Электрондық чек: <urlsafe>|}")
add("kk", "safe", "work",
    "<name>, {есеп|презентация|шарт} {дайын|келісуде}. <time>-де {кездесу|онлайн-кездесу} {кеңседе|Zoom-да}. {Түзетулерді ертеңге дейін жіберіңіз.|}",
    "{Шұғыл|Маңызды}: {жиналыс <time>-ге ауыстырылды|клиент <time>-ге дейін жауап күтеді}. {Қатысуыңызды растаңыз.|}")

add("kk", "fraud", "bank_phish",
    "{<bank> қауіпсіздік қызметі|<bank>}: {жеке кабинетіңізде|профиліңізде} {күдікті әрекет анықталды|жаңа құрылғыдан кіру тіркелді}. {Қаражатты қорғау үшін|Бұғаттаудан сақтану үшін} {сілтеме бойынша кіріңіз|сайтқа кіріп, растаңыз}: <urlphish>",
    "{Құрметті клиент|Қадірлі клиент}, {құпия сөзіңіздің мерзімі аяқталды|деректеріңіз ескірді}. {Мәліметтерді жаңартыңыз|Деректерді растаңыз} {24 сағат ішінде|тез арада}: <urlphish>")
add("kk", "fraud", "cvv_code",
    "{Қауіпсіздік қызметінің қызметкері|<bank> маманы}: {күдікті операцияны|<amt> сомасын} {болдырмау үшін|тоқтату үшін} {SMS-тағы кодты|CVV кодты|пин-кодты} {айтыңыз|жіберіңіз}.",
    "Сізге <bank> {қызметкері|маманы} {қоңырау шалады|қоңырау шалды}. Оған {картаның артындағы үш таңбалы кодты|осы хабарламадағы кодты: <code>} {айтыңыз|жіберіңіз}, {деректерді салыстыру үшін|шотты қорғау үшін}.")
add("kk", "fraud", "card_block",
    "Картаңыз {бұғатталды|шектелді|бұғатталады}{!|.} {Жедел түрде|Дереу|Бүгін} {деректерді растаңыз|картаны ашыңыз} {мына сілтеме арқылы|сайтта}: <urlphish>",
    "<bank>: *<card4> картасына қолжетімділік шектелді. {Шектеуді алу үшін|Картаны қолдануды жалғастыру үшін} {сілтемеге өтіңіз|тексеруден өтіңіз}: <urlphish>")
add("kk", "fraud", "delivery_customs",
    "Сіздің сәлемдемеңіз {кеденде|қоймада} {тұр|ұсталды}. {Кеден алымын|Жеткізу бойынша қосымша төлемді} <amt> {<date> дейін|48 сағат ішінде} төлеңіз: <urlphish>",
    "№<num> сәлемдемені {жеткізу мүмкін болмады|курьер жеткізе алмады}. {Мекенжайды нақтылаңыз|Жеткізу мекенжайын жаңартыңыз} {және сақтау ақысын <amt> төлеңіз|}: <urlphish>")
add("kk", "fraud", "gov_payment",
    "{Мемлекеттік|Қаржы министрлігінің} {әлеуметтік төлем|өтемақы|салықты қайтару} <amt> {сізге мақұлданды|сізге тиесілі}. {Төлемді алыңыз|Қаражатты рәсімдеңіз} {<date> дейін|3 күн ішінде}: <urlphish>",
    "{Сізге жәрдемақы есептелді|Салық шегерімі мақұлданды}. {Картаға түсу үшін|Ақшаны алу үшін} {сауалнаманы толтырыңыз|карта деректерін көрсетіңіз}: <urlphish>")
add("kk", "fraud", "prize",
    "{Құттықтаймыз|Сіз бақытты иегерсіз}! Сіз <org> {ұтыс ойынында|акциясында} {жүлде|смартфон|көлік|<amt>} {ұттыңыз|жеңіп алдыңыз}. {Жүлдені алыңыз|Ұтысты алу үшін өтіңіз}: <urlphish>",
    "{Нөміріңіз таңдалды|Сіз жеңімпаз атандыңыз}! {Сыйлықты алу үшін|Ұтысты алу үшін} {комиссия <amt> төлеңіз|осы хабарламаға жауап беріңіз|<urlphish> сілтемесіне өтіңіз}.")
add("kk", "fraud", "money_transfer",
    "{Қайырлы күн|Сәлеметсіз бе}! {Мен <org> бухгалтериясынан <name>|Сізге <name> жазып тұр}. {Қателесіп|Байқаусызда} <amt> {аударылып кетті|жібердік}, {<phone> нөміріне қайтарып жіберіңізші|*<card4> картасына қайтарыңызшы}.")
add("kk", "fraud", "relative",
    "{Ана|Әже|Әке}, {мен апатқа ұшырадым|полициямен мәселе болды|ауруханадамын}. {Шұғыл|Тез} <amt> {осы нөмірге <phone> аудар|картаға аудар}, {кейін түсіндіремін|телефоным сынды, бөтен нөмірден жазып тұрмын}.",
    "{Сәлем, мен <name>|Мен сенің ұлыңмын}, {нөмірімді ауыстырдым|телефоным бұзылды}. <amt> {аударып жіберші, кейін қайтарамын|шұғыл аудар, кейін айтамын}.")
add("kk", "fraud", "investment",
    "{Инвестиция|Криптовалюта|Биржада сауда}: {табыс|пайда} {аптасына 30%-дан|күніне <amt>-ге дейін}! {Қайтарым кепілдігі|Қауіпсіз}. {Чатқа|Telegram-ға} {қосыл|кіріңіз} @<handle>.",
    "{Таныс брокерім|Біздің талдаушы} {бір схема көрсетті|стратегиямен бөлісті}: <amt> салып, бір аптада үш есе алдым. {Сен де қалайсың ба|Жаз}? @<handle>")
add("kk", "fraud", "tech_support",
    "{Қолдау қызметі|Техникалық қолдау} <org>: {аккаунтыңыз бұзылды|құрылғыңызға вирус түсті}. {Қорғаныс қосымшасын|Қашықтан көмек бағдарламасын} {мына сілтемеден жүктеңіз|орнатыңыз}: <urlphish>",
    "{Маман|Қолдау қызметі}: {телефоныңыздан вирус анықтадық|компьютеріңіз зақымданған}. {<phone> нөміріне қоңырау шалыңыз|@<handle> чатына жазыңыз}, {құрылғыны өшірмеңіз|біз көмектесеміз}.")
add("kk", "fraud", "debt",
    "{Хабарлама|Шақыру қағазы}: {сізде <amt> берешек бар|сіздің атыңызда <amt> қарыз тіркелген} {несие бойынша|салық бойынша|коммуналдық қызмет бойынша}. {<date> дейін|Бүгін} {төлеңіз|өтеңіз}, {әйтпесе сотқа беріледі|әйтпесе іс сот орындаушыларына жолданады}: <urlphish>")
add("kk", "fraud", "account_pwd",
    "{Аккаунтыңыз|<org> тіркелгіңіз} {24 сағаттан кейін|бүгін} {жойылады|бұғатталады}. {Құпия сөзді растаңыз|Кіруді қалпына келтіріңіз} {осы жерде|сілтеме бойынша}: <urlphish>",
    "{Біреу аккаунтыңызға кіруге тырысты|Жаңа құрылғыдан кіру анықталды}. {Бұл сіз болмасаңыз|Қорғау үшін} {құпия сөзді ауыстырыңыз|логин мен құпия сөзді енгізіңіз}: <urlphish>")
add("kk", "fraud", "fake_job",
    "{Сәлеметсіз бе|Қайырлы күн}! {Резюмеңізді көрдік|Қашықтан жұмысқа шақырамыз}. {Табыс|Төлем} {күніне|ауысымына} <amt>, {тәжірибесіз|еркін кесте}. {Тапсырмалар телефоннан орындалады|Оқыту тегін}. WhatsApp-қа <phone> жазыңыз.",
    "{Көмекшілер|Операторлар} {керек|қабылданады} {үйден|онлайн}: {лайк|пікір|тапсырыс}, {төлем бірден|табыс <amt>}. {Бүгін баста|Жаз} @<handle>")
add("kk", "fraud", "bonus_refund",
    "Сізге <amt> {бонус|кэшбэк|қайтарым} {есептелді|қолжетімді}. {Оны белсендіріңіз|Бонусты алыңыз} {<date> дейін|апта соңына дейін}: <urlphish>",
    "{Ақшаңызды қайтарамыз|Сізге өтемақы тиесілі} {сатып алу үшін|байланыс қызметі үшін}. {Карта нөмірін көрсетіңіз|Карта деректерін қалдырыңыз} {<amt> алу үшін|есептеу үшін}: <urlphish>")
add("kk", "fraud", "fear_secrecy",
    "{Соңғы ескерту|Назар аударыңыз}. {Деректеріңіз|Суреттеріңіз} {желіге түсті|белгілі болды}. {Ешкімге айтпаңыз|Полицияға жүгінбеңіз}, {әйтпесе|салдарынан аулақ болу үшін} {<amt> аударыңыз|@<handle> жазыңыз}.",
    "{Сізге қатысты|Сізден} {алаяқтық бойынша|заң бұзу бойынша} өтініш түсті. {Дереу <phone> нөміріне қоңырау шалыңыз|Келу міндетті}. {Әңгіме құпия|Ешкімге айтпаңыз}.")
add("kk", "suspicious", "loan_ad", "Жедел несие {<amt> дейін|бас тартусыз} {5 минутта|картаға}. {Толығырақ|Рәсімдеу}: <urlsus>")
add("kk", "suspicious", "otp_nowarn", "Кодыңыз: <code>. Оны <org> сайтына енгізіңіз.")
add("kk", "suspicious", "unknown_link", "Сәлем, мынаны қарашы: <urlsus>")

# ============================ EN ============================
add("en", "safe", "chat",
    "{Hey|Hi|Yo} <name>, {are you coming|you still up for coming} to {the gym|dinner|the game} {tonight|tomorrow}? I'll be {there|at the entrance} around <time>.",
    "<name> {text me|call me} when you're {free|home}. {Can you grab milk on the way?|Dinner's at seven, don't be late.|Running ten min late, sorry!}")
add("en", "safe", "family",
    "{Mom|Dad|Grandma}: {don't forget|remember} {about} {the birthday dinner|Saturday's trip|the family party}. {Love you!|Call me tonight.|See you soon.}",
    "<name>, {thanks for the gift|happy birthday|congrats on the new job}! {Hugs|Can't wait to see you|Let's catch up this weekend}.")
add("en", "safe", "delivery",
    "Your order #<num> {has shipped|is out for delivery|is ready for pickup} and {will arrive|should arrive} <date>.{ Track it: <urlsafe>|}",
    "Courier will {arrive|be there} <date> {between 10 and 2|after 6 pm}. {Driver phone: <phone>|No payment needed, already paid.}")
add("en", "safe", "bank_notice",
    "<bank>: {purchase|payment|charge} of <amt> at <place>, card ending <card4>. {Available balance: <amt>.|}",
    "<bank>: {deposit|transfer} of <amt> {received|posted} to card ending <card4>. {If this wasn't you, call the number on the back of your card.|}",
    "<bank>: at your request, card ending <card4> has been {temporarily locked|frozen}. {You can unlock it in the app or at a branch.|}")
add("en", "safe", "otp",
    "Your {verification|one-time} code is <code>. {Do not share it with anyone|Never share this code}, {even bank staff|including <bank> employees}.",
    "<code> is your code to {log in to|confirm <amt> payment at} <org>. {It expires in 5 minutes.|If you didn't request it, ignore this message.}")
add("en", "safe", "reminder",
    "{Reminder|Friendly reminder}: {doctor's appointment|meeting|dentist|class} on <date> at <time>. {Reply C to confirm|Address: <place>|To reschedule call <phone>}.")
add("en", "safe", "gov_edu",
    "{University|School|Registrar}: {class|exam|parent meeting} {moved to|scheduled for} <date>, <time>. {Room <num>.|}",
    "{DMV|Tax office|City hall}: {your documents are ready|your application was received|walk-ins by appointment only}. {Ref <num>.|Details at <urlgov>}",
    "{Tax office|City hall}: your {fine|balance} of <amt> has been {paid|settled}. Thank you.")
add("en", "safe", "ads",
    "<org>: {up to 30% off|big sale|new arrivals} {in store|online|in the app} {until <date>|this weekend only}. {Reply STOP to opt out|Details: <urlsafe>}")
add("en", "safe", "purchase",
    "{Thanks for shopping|Receipt} at <org>. {Total|Amount}: <amt>.{ E-receipt: <urlsafe>|}")
add("en", "safe", "work",
    "<name>, the {report|deck|contract} is {ready|with legal}. {Call at|Meeting at} <time> {in the conference room|on Zoom}. {Edits needed by tomorrow.|}",
    "{Urgent|Important}: {standup moved to <time>|client needs an answer by <time>}. {Please confirm.|}")

add("en", "fraud", "bank_phish",
    "{<bank> Security|<bank>}: {unusual activity|a new-device login} {was detected|was flagged} on your {account|profile}. {To protect your funds|To avoid suspension} {log in|verify}: <urlphish>",
    "{Dear customer|Valued client}, your {password has expired|details are out of date}. {Update|Confirm} your information {within 24 hours|now}: <urlphish>")
add("en", "fraud", "cvv_code",
    "{<bank> fraud team|Security officer}: {to cancel|to block} {a suspicious transaction|a charge of <amt>}, {reply with|read out} {your PIN|the CVV|the code we sent}.",
    "A {<bank> representative|specialist} {will call|just called} you. {Give them|Read them} {the 3-digit code on the back of your card|the code in this message: <code>} {to verify your identity|to secure your account}.")
add("en", "fraud", "card_block",
    "Your card has been {blocked|restricted|suspended}{!|.} {Verify your details|Unlock it} {now|today|immediately}: <urlphish>",
    "<bank>: access to card ending <card4> is {limited|paused}. {To restore it|To keep using your card} {complete a quick check|verify here}: <urlphish>")
add("en", "fraud", "delivery_customs",
    "Your parcel is {held at customs|on hold}. {Pay|You must pay} {a customs fee|a redelivery fee} of <amt> {by <date>|within 48 hours}: <urlphish>",
    "We {couldn't deliver|missed you} parcel #<num>. {Confirm your address|Update delivery details} {and pay storage <amt>|}: <urlphish>")
add("en", "fraud", "gov_payment",
    "{Treasury|Tax Agency|Government}: {you are eligible for|you've been approved for} a {tax refund|relief payment|benefit} of <amt>. {Claim|Collect} it {by <date>|within 3 days}: <urlphish>",
    "{Your relief payment is ready|Your refund was approved}. {To receive funds|To get your money} {fill in the form|enter your card details}: <urlphish>")
add("en", "fraud", "prize",
    "{Congratulations|You're our lucky winner}! You {won|have been selected for} {a gift card|a new phone|a car|<amt>} in the <org> {draw|promo}. {Claim|Collect} {your prize|it}: <urlphish>",
    "{Your number was picked|You're a winner}! {To get your prize|To claim your reward} {pay a small fee of <amt>|reply YES|tap <urlphish>}.")
add("en", "fraud", "money_transfer",
    "{Hello|Hi}, {this is <name> from <org>|accounting here}. We {mistakenly sent|transferred by mistake} <amt> to you, {please send it back to <phone>|please return it to card ending <card4>}.")
add("en", "fraud", "relative",
    "{Mom|Grandma|Dad}, {I had an accident|I'm in trouble with the police|I'm in hospital}. {Please send|I need} <amt> {to this number <phone>|urgently}, {I'll explain later|my phone broke, texting from a friend's}.",
    "{Hi, it's <name>|It's your son}, {new number|phone is broken}. {Can you send|Please transfer} <amt> {now, I'll pay you back|urgently, long story}.")
add("en", "fraud", "investment",
    "{Investing|Crypto|Trading}: {profit|returns} {from 30% a week|up to <amt> a day}! {Guaranteed|Zero risk}. {Join|Message} @<handle>.",
    "{A broker friend|Our analyst} {showed me|shared} {a strategy|a trick}: {put in <amt>, tripled it|made triple in a week}. {Want in|Text me}? @<handle>")
add("en", "fraud", "tech_support",
    "<org> {Support|Help desk}: your {account|device} {was hacked|is infected}. {Install|Download} {a protection app|our remote-help tool} {here|now}: <urlphish>",
    "{Support agent|Technician}: {we detected a virus on your phone|your computer is infected}. {Call <phone>|Message @<handle>}, {do not turn off the device|we'll help}.")
add("en", "fraud", "debt",
    "{Notice|Final summons}: {you owe|an outstanding balance of} <amt> {on your loan|in taxes|in utility bills}. {Pay|Settle} {by <date>|today} {to avoid court|or the case goes to bailiffs}: <urlphish>")
add("en", "fraud", "account_pwd",
    "Your <org> {account|login} will be {deleted|locked} {in 24 hours|today}. {Confirm your password|Restore access} {here|now}: <urlphish>",
    "{Someone tried to log in|A new-device login was detected}. {If it wasn't you|To protect it} {reset your password|enter your login and password}: <urlphish>")
add("en", "fraud", "fake_job",
    "{Hello|Hi}! {We saw your resume|We're hiring remote staff}. {Pay|Earn} <amt> {per day|per shift}, {no experience|flexible hours}. {Tasks done on your phone|Free training}. {Text|Message} WhatsApp <phone>.",
    "{Assistants|Operators} {needed|wanted} {from home|online}: {likes|reviews|orders}, {paid instantly|earn <amt>}. {Start today|Text} @<handle>")
add("en", "fraud", "bonus_refund",
    "A {bonus|cashback|refund} of <amt> {from <bank>|is available}. {Activate|Claim} it {by <date>|before the weekend}: <urlphish>",
    "{We'll refund you|You're owed compensation} {for your purchase|for service charges}. {Enter your card number|Leave your card details} {to receive <amt>|so we can pay you}: <urlphish>")
add("en", "fraud", "fear_secrecy",
    "{Final warning|Attention}. {Your data|Your photos} {leaked|were exposed}. {Tell no one|Don't call the police}, {or else|to avoid consequences} {send <amt>|message @<handle>}.",
    "{A complaint was filed against you for|You're under investigation for} {fraud|violation}. {Call <phone> immediately|Appearance mandatory}. {This is strictly confidential|Don't tell anyone}.")
add("en", "suspicious", "loan_ad", "{Fast loan|Quick cash} {up to <amt>|no refusal} {in 5 minutes|to your card}. {Details|Apply}: <urlsus>")
add("en", "suspicious", "otp_nowarn", "Your code: <code>. Enter it on the <org> site.")
add("en", "suspicious", "unknown_link", "Hey, {it's <name>|you don't know me}. {Look at this|Check this out}: <urlsus>")

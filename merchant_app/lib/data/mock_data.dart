import 'models.dart';

/// Mock datasets copied verbatim from 02-merchant-dashboard.jsx so every screen
/// renders exactly as the design before the real API exists (Phase 4 swaps the
/// repository implementation behind a flag — screens never change).

const List<Branch> kBranches = [
  Branch(
    id: 132,
    name: {'en': 'Divinia Clinic — Olaya', 'ar': 'عيادة ديفينيا — العليا'},
    addr: {'en': 'Olaya St, Riyadh 12211, KSA', 'ar': 'شارع العليا، الرياض ١٢٢١١'},
  ),
  Branch(
    id: 101,
    name: {'en': 'Divinia Clinic — Al Nakheel', 'ar': 'عيادة ديفينيا — النخيل'},
    addr: {
      'en': 'King Fahd Rd, Al Nakheel, Riyadh 12382',
      'ar': 'طريق الملك فهد، النخيل، الرياض ١٢٣٨٢'
    },
  ),
  Branch(
    id: 140,
    name: {'en': 'Divinia Clinic — Jeddah', 'ar': 'عيادة ديفينيا — جدة'},
    addr: {'en': 'Prince Sultan Rd, Jeddah 23615', 'ar': 'طريق الأمير سلطان، جدة ٢٣٦١٥'},
  ),
];

const List<Service> kServices = [
  Service(
    id: 'botox',
    en: 'Botox',
    ar: 'بوتوكس',
    cat: 'Injectables',
    price: 900,
    dur: 30,
    about: {
      'en':
          'A quick, precise injectable that relaxes targeted muscles to soften lines on the forehead, brows, and around the eyes. Results appear within 3–7 days.',
      'ar':
          'حقن دقيق وسريع يرخي العضلات المستهدفة لتنعيم الخطوط على الجبهة والحاجبين وحول العينين. تظهر النتائج خلال ٣ إلى ٧ أيام.'
    },
    tiers: [
      Tier({'en': '1 area', 'ar': 'منطقة واحدة'}, 900),
      Tier({'en': '2 areas', 'ar': 'منطقتان'}, 1600),
      Tier({'en': '3 areas', 'ar': '٣ مناطق'}, 2200),
    ],
    prep: {
      'en': 'Avoid blood thinners and alcohol 24h before. Arrive with a clean, makeup-free face.',
      'ar': 'تجنّب مميّعات الدم والكحول قبل ٢٤ ساعة. احضر بوجه نظيف خالٍ من المكياج.'
    },
    after: {
      'en': "Stay upright 4 hours, skip strenuous exercise for 24h, don't rub the area.",
      'ar': 'ابقَ منتصباً ٤ ساعات، تجنّب التمارين الشاقة ٢٤ ساعة، ولا تفرك المنطقة.'
    },
  ),
  Service(
    id: 'filler',
    en: 'Dermal Fillers',
    ar: 'الفيلر الجلدي',
    cat: 'Injectables',
    price: 1600,
    dur: 45,
    about: {
      'en':
          'Hyaluronic-acid fillers restore volume and contour to lips, cheeks, and jawline. Results are immediate and last 9–12 months.',
      'ar':
          'فيلر حمض الهيالورونيك يعيد الحجم والتحديد للشفاه والخدود وخط الفك. النتائج فورية وتدوم من ٩ إلى ١٢ شهراً.'
    },
    tiers: [
      Tier({'en': 'Lip', 'ar': 'الشفاه'}, 1600),
      Tier({'en': 'Cheek', 'ar': 'الخدود'}, 2100),
      Tier({'en': 'Jawline', 'ar': 'خط الفك'}, 2600),
    ],
    prep: {
      'en': 'Avoid blood thinners 24h before. Tell us about any cold sores.',
      'ar': 'تجنّب مميّعات الدم قبل ٢٤ ساعة. أخبرنا بأي قرح باردة.'
    },
    after: {
      'en': 'Mild swelling is normal for 48h. Apply ice, avoid heat and pressure.',
      'ar': 'التورّم الخفيف طبيعي لمدة ٤٨ ساعة. ضع الثلج وتجنّب الحرارة والضغط.'
    },
  ),
  Service(
    id: 'hydra',
    en: 'HydraFacial',
    ar: 'هيدرافيشل',
    cat: 'Facials',
    price: 650,
    dur: 50,
    about: {
      'en':
          'A multi-step facial that cleanses, exfoliates, and hydrates with a gentle vortex system. No downtime, instant glow.',
      'ar':
          'علاج متعدّد الخطوات ينظّف ويقشّر ويرطّب البشرة بنظام لطيف. بلا فترة نقاهة، ونضارة فورية.'
    },
    tiers: [
      Tier({'en': 'Signature', 'ar': 'الأساسي'}, 650),
      Tier({'en': 'Deluxe', 'ar': 'المطوّر'}, 900),
      Tier({'en': 'Platinum', 'ar': 'البلاتيني'}, 1200),
    ],
    prep: {
      'en': 'Skip retinol and exfoliants 48h before. Come with clean skin.',
      'ar': 'تجنّب الريتينول والمقشّرات قبل ٤٨ ساعة. احضر ببشرة نظيفة.'
    },
    after: {
      'en': 'Use SPF, avoid direct sun and saunas for 24h.',
      'ar': 'استخدم واقي الشمس وتجنّب الشمس المباشرة والساونا ٢٤ ساعة.'
    },
  ),
  Service(
    id: 'laser',
    en: 'Laser Hair Removal',
    ar: 'إزالة الشعر بالليزر',
    cat: 'Laser',
    price: 400,
    dur: 40,
    about: {
      'en':
          'Diode laser targets hair follicles for lasting reduction. A course of 6–8 sessions gives the best results.',
      'ar': 'ليزر الدايود يستهدف بصيلات الشعر لتقليل دائم. جلسات من ٦ إلى ٨ تعطي أفضل النتائج.'
    },
    tiers: [
      Tier({'en': 'Small area', 'ar': 'منطقة صغيرة'}, 400),
      Tier({'en': 'Medium area', 'ar': 'منطقة متوسطة'}, 700),
      Tier({'en': 'Full body', 'ar': 'الجسم كامل'}, 1500),
    ],
    prep: {
      'en': 'Shave the area 24h before. No waxing, tanning, or sun for 2 weeks prior.',
      'ar': 'احلق المنطقة قبل ٢٤ ساعة. تجنّب الشمع والتسمير والشمس لأسبوعين قبلها.'
    },
    after: {
      'en': 'Avoid sun, hot showers, and gyms for 48h. Use SPF daily.',
      'ar': 'تجنّب الشمس والاستحمام الساخن والنوادي ٤٨ ساعة. استخدم واقي الشمس يومياً.'
    },
  ),
  Service(
    id: 'prp',
    en: 'PRP Hair Treatment',
    ar: 'علاج الشعر بالبلازما',
    cat: 'Restorative',
    price: 1200,
    dur: 60,
    about: {
      'en':
          'Platelet-rich plasma from your own blood is injected into the scalp to stimulate hair growth over a course of sessions.',
      'ar':
          'البلازما الغنية بالصفائح من دمك تُحقن في فروة الرأس لتحفيز نمو الشعر عبر عدة جلسات.'
    },
    tiers: [
      Tier({'en': 'Single session', 'ar': 'جلسة واحدة'}, 1200),
      Tier({'en': 'Package of 3', 'ar': 'باقة ٣ جلسات'}, 3200),
    ],
    prep: {
      'en': 'Hydrate well and eat before your visit. Avoid blood thinners 3 days prior.',
      'ar': 'اشرب الماء وتناول الطعام قبل الزيارة. تجنّب مميّعات الدم ٣ أيام قبلها.'
    },
    after: {
      'en': "Don't wash hair for 6 hours. Avoid heat styling for 48h.",
      'ar': 'لا تغسل الشعر ٦ ساعات. تجنّب التصفيف الحراري ٤٨ ساعة.'
    },
  ),
  Service(
    id: 'consult',
    en: 'Skin Consultation',
    ar: 'استشارة جلدية',
    cat: 'Consultation',
    price: 200,
    dur: 20,
    about: {
      'en':
          'A one-on-one assessment with a female dermatologist to map a personalized treatment plan for your skin.',
      'ar': 'تقييم فردي مع طبيبة جلدية لوضع خطة علاج مخصّصة لبشرتك.'
    },
    tiers: [
      Tier({'en': 'Standard', 'ar': 'عادية'}, 200),
      Tier({'en': 'With skin analysis', 'ar': 'مع تحليل البشرة'}, 350),
    ],
    prep: {
      'en': 'Come with a clean face and a list of products you use.',
      'ar': 'احضري بوجه نظيف وقائمة بالمنتجات التي تستخدمينها.'
    },
    after: {
      'en': "You'll receive a written plan and quotes by SMS.",
      'ar': 'ستصلك خطة مكتوبة وعروض أسعار عبر SMS.'
    },
  ),
];

const List<Convo> kConvos = [
  Convo(
    name: 'Nour A.',
    phone: '+966 55 214 8890',
    time: '2:02 PM',
    tag: 'booked',
    lang: 'ar',
    summary:
        'Caller asked to book Botox for next Tuesday. Agent offered morning or evening, confirmed 6:00 PM, sent an SMS confirmation and set a 24-hour reminder.',
    treatment: 'Botox · 3 areas',
    price: 2200,
    sentiment: 'Positive',
    dur: '01:12',
  ),
  Convo(
    name: '+966 50 771 3320',
    phone: '+966 50 771 3320',
    time: '1:37 PM',
    tag: 'call',
    lang: 'ar',
    summary:
        'Caller asked how long dermal filler lasts and whether a female doctor is available. Agent answered 9–12 months and confirmed a female doctor, then offered a consultation.',
    sentiment: 'Positive',
    dur: '00:58',
  ),
  Convo(
    name: 'Layla M.',
    phone: '+966 56 902 4471',
    time: '12:20 PM',
    tag: 'msg',
    lang: 'ar',
    summary:
        "WhatsApp: patient asked to reschedule Thursday's HydraFacial. Agent moved it to Saturday 5:00 PM and re-sent the confirmation.",
    sentiment: 'Neutral',
    dur: '—',
  ),
  Convo(
    name: 'Sara K.',
    phone: '+966 53 118 6642',
    time: '11:05 AM',
    tag: 'call',
    lang: 'en',
    summary:
        'English caller asked laser hair removal pricing and pre-treatment prep. Agent quoted 400 SAR/session and shared prep guidance, then booked a session for Sunday.',
    treatment: 'Laser · 1 session',
    price: 400,
    sentiment: 'Positive',
    dur: '02:03',
  ),
  Convo(
    name: '+966 59 440 1187',
    phone: '+966 59 440 1187',
    time: '10:41 AM',
    tag: 'call',
    lang: 'ar',
    summary:
        'Caller reported swelling after fillers and asked what to avoid. Agent flagged it as urgent and transferred to the on-call clinician.',
    sentiment: 'Concerned',
    dur: '01:44',
    urgent: true,
  ),
];

const List<Faq> kFaqs = [
  Faq('How do I book an appointment?', 'كيف أحجز موعداً؟',
      'You can book right over the phone or WhatsApp — the agent confirms instantly with an SMS.',
      'يمكنك الحجز مباشرة عبر الهاتف أو واتساب، وسيؤكد المساعد موعدك فوراً برسالة SMS.'),
  Faq('How much is Botox?', 'كم سعر البوتوكس؟', 'Botox starts from SAR 900 per area.',
      'يبدأ البوتوكس من ٩٠٠ ريال لكل منطقة.'),
  Faq('How long do fillers last?', 'كم تدوم الفيلر؟', 'Dermal fillers typically last 9–12 months.',
      'تدوم الفيلر عادةً من ٩ إلى ١٢ شهراً.'),
  Faq('Can I reschedule my appointment?', 'هل يمكنني تغيير موعدي؟',
      'Yes — just ask the agent and it will move your booking and re-send the confirmation.',
      'نعم — فقط اطلب من المساعد وسيغيّر حجزك ويعيد إرسال التأكيد.'),
  Faq('Do you have female doctors?', 'هل لديكم طبيبات؟',
      'Yes, female dermatologists are available on request.', 'نعم، تتوفّر طبيبات جلدية عند الطلب.'),
  Faq('How should I prepare before laser?', 'كيف أستعد قبل الليزر؟',
      'Shave the area 24h before and avoid sun or tanning for two weeks prior.',
      'احلق المنطقة قبل ٢٤ ساعة وتجنّب الشمس أو التسمير لأسبوعين قبلها.'),
  Faq('What should I avoid after treatment?', 'ما الذي يجب تجنّبه بعد العلاج؟',
      'Avoid heat, direct sun, and strenuous exercise for 24–48 hours.',
      'تجنّب الحرارة والشمس المباشرة والتمارين الشاقة لمدة ٢٤ إلى ٤٨ ساعة.'),
];

const List<Appt> kAppts = [
  Appt(
      name: 'Nour A.',
      svc: {'en': 'Botox · 3 areas', 'ar': 'بوتوكس · ٣ مناطق'},
      day: {'en': 'Tue', 'ar': 'الثلاثاء'},
      date: '18',
      time: '6:00 PM',
      via: 'AI · Voice'),
  Appt(
      name: 'Sara K.',
      svc: {'en': 'Laser Hair Removal', 'ar': 'إزالة الشعر بالليزر'},
      day: {'en': 'Sun', 'ar': 'الأحد'},
      date: '16',
      time: '3:30 PM',
      via: 'AI · Voice'),
  Appt(
      name: 'Layla M.',
      svc: {'en': 'HydraFacial', 'ar': 'هيدرافيشل'},
      day: {'en': 'Sat', 'ar': 'السبت'},
      date: '15',
      time: '5:00 PM',
      via: 'AI · WhatsApp'),
  Appt(
      name: 'Huda R.',
      svc: {'en': 'Skin Consultation', 'ar': 'استشارة جلدية'},
      day: {'en': 'Mon', 'ar': 'الإثنين'},
      date: '17',
      time: '2:00 PM',
      via: 'AI · Voice'),
];

const List<Holiday> kHolidays = [
  Holiday(
    name: {'en': 'Saudi National Day', 'ar': 'اليوم الوطني السعودي'},
    date: {'en': 'Sep 23, 2026', 'ar': '٢٣ سبتمبر ٢٠٢٦'},
    closed: true,
    hours: '',
    upcoming: true,
  ),
  Holiday(
    name: {'en': 'Eid al-Fitr', 'ar': 'عيد الفطر'},
    date: {'en': 'Mar 20, 2026', 'ar': '٢٠ مارس ٢٠٢٦'},
    closed: false,
    hours: '4:00 PM → 9:00 PM',
    upcoming: false,
  ),
];

const List<int> kVol = [
  52, 38, 41, 47, 44, 58, 92, 49, 43, 55, 46, 61, 40, 97, //
  45, 50, 44, 38, 33, 79, 62, 48, 52, 41, 58, 33, 120, 64
];

const Map<String, List<Report>> kReports = {
  'call': [
    Report(id: 'volume', en: 'Call Volume Trends', ar: 'اتجاهات حجم المكالمات', chart: 'line', descEn: 'Number of calls received over time', descAr: 'عدد المكالمات المستلمة عبر الوقت'),
    Report(id: 'duration', en: 'Call Duration Breakdown', ar: 'تحليل مدة المكالمات', chart: 'bar', descEn: 'How long calls typically last', descAr: 'المدة المعتادة للمكالمات'),
    Report(id: 'sentiment', en: 'Average Sentiment', ar: 'متوسط المشاعر', chart: 'donut', descEn: 'Caller mood across conversations', descAr: 'مشاعر المتصلين عبر المحادثات'),
    Report(id: 'peak', en: 'Peak Hours Analysis', ar: 'تحليل ساعات الذروة', chart: 'bar', descEn: 'Busiest hours of the day', descAr: 'أكثر ساعات اليوم ازدحاماً'),
    Report(id: 'afterhours', en: 'After-Hours Calls Served', ar: 'مكالمات بعد ساعات العمل', chart: 'line', descEn: 'Calls the agent captured while closed', descAr: 'المكالمات التي التقطها المساعد بعد الإغلاق'),
  ],
  'orders': [
    Report(id: 'bookvol', en: 'Booking Volume Trends', ar: 'اتجاهات حجم الحجوزات', chart: 'line', descEn: 'Appointments booked over time', descAr: 'المواعيد المحجوزة عبر الوقت'),
    Report(id: 'revenue', en: 'Revenue Trends', ar: 'اتجاهات الإيرادات', chart: 'line', descEn: 'Treatment revenue over time', descAr: 'إيرادات العلاجات عبر الوقت'),
    Report(id: 'bytreatment', en: 'Bookings by Treatment', ar: 'الحجوزات حسب العلاج', chart: 'hbar', descEn: 'Which treatments book the most', descAr: 'أكثر العلاجات حجزاً'),
    Report(id: 'channel', en: 'Booking Channel Split', ar: 'قنوات الحجز', chart: 'donut', descEn: 'Voice vs WhatsApp vs web', descAr: 'الصوت مقابل واتساب مقابل الويب'),
  ],
};

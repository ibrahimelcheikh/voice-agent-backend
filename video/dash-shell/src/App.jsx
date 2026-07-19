import React, { useState } from "react";
import {
  Home, Phone, Sparkles, PieChart, Calendar, Settings as SettingsIcon,
  HelpCircle, Menu as MenuIcon, X, Search, ChevronDown, ChevronLeft, ChevronRight,
  Clock, Users, PhoneCall, MessageSquare, Play, Mic, CalendarCheck, ArrowUpRight,
  Globe, Pause, PhoneIncoming, CheckCircle2, AlertTriangle, MapPin, Plus, ArrowLeft,
  Timer, ShieldCheck, Smile, TrendingUp, Check
} from "lucide-react";

const C = {
  bg: "#EFE9DF", card: "#FDFBF7", cardAlt: "#F5F0E7", ink: "#1B2431", sub: "#6B7280",
  line: "#EAE3D6", blue: "#2E6BFF", blueDeep: "#1E4FD8", blueSoft: "#E7EEFF",
  green: "#3FB27F", greenSoft: "#E4F5EC", amber: "#E8934A", amberSoft: "#FBEAD9",
  rose: "#E76A8B", roseSoft: "#FBE6EC", violet: "#7C6BE8", violetSoft: "#ECE9FC",
};

const BRANCHES = [
  { id: 132, name: { en: "Divinia Clinic — Olaya", ar: "عيادة ديفينيا — العليا" }, addr: { en: "Olaya St, Riyadh 12211, KSA", ar: "شارع العليا، الرياض ١٢٢١١" } },
  { id: 101, name: { en: "Divinia Clinic — Al Nakheel", ar: "عيادة ديفينيا — النخيل" }, addr: { en: "King Fahd Rd, Al Nakheel, Riyadh 12382", ar: "طريق الملك فهد، النخيل، الرياض ١٢٣٨٢" } },
  { id: 140, name: { en: "Divinia Clinic — Jeddah", ar: "عيادة ديفينيا — جدة" }, addr: { en: "Prince Sultan Rd, Jeddah 23615", ar: "طريق الأمير سلطان، جدة ٢٣٦١٥" } },
];

const T = {
  en: {
    dir: "ltr", brandSub: "Divinia Clinic", active: "Active — Handling calls",
    greeting: "Good afternoon, Divinia", todayIs: "It's Saturday, 2:14 PM",
    earned: "You've booked", earnedTail: "in treatments this month",
    staffHours: "Staff Hours Reclaimed", thisMonth: "This month",
    extraCalls: "After-Hours Calls Captured", bookings: "Appointments Booked",
    popular: "Popular Times Today", live: "Live 2 PM", optimize: "Optimize your agent",
    tipTitle: "Enable Arabic voice", tipBody: "Most Riyadh callers prefer Arabic. Turn on the Khaleeji female voice so the agent greets them in their language.",
    configure: "Configure", recent: "Recent Activity", recentSub: "Latest calls, messages, and bookings across your clinic.",
    viewAll: "View all", callCompleted: "Call completed", booked: "Appointment booked", msg: "WhatsApp message",
    convosTitle: "Conversations", convosSub: "Every call and chat your agent handled.", searchConvos: "Search conversations…",
    ordersOnly: "Bookings only", dateRange: "Date range", apply: "Apply", cancel: "Cancel",
    play: "Play", sentiment: "Sentiment",
    servicesTitle: "Services", servicesSub: "Treatments your agent can quote and book.", searchServices: "Search treatments…",
    featured: "Featured recommendations", featuredSub: "The agent suggests these contextually during calls.",
    addRec: "Add recommendation", from: "from", book: "bookable", bookNow: "Book appointment",
    duration: "Duration", prep: "Before your visit", aftercare: "After care", tiers: "Options & pricing", about: "About this treatment",
    reportsTitle: "Detailed Reports", reportsSub: "Explore in-depth analytics and insights.",
    callAnalytics: "Call Analytics", callAnalyticsSub: "Deep dive into call metrics and trends.",
    ordersRevenue: "Bookings & Revenue", ordersRevenueSub: "Analyze appointment volume and revenue.",
    totalCalls: "Total Calls", totalCallsSub: "Total number of calls",
    avgCalls: "Average Calls", avgCallsSub: "Daily average", back: "Back",
    apptsTitle: "Appointments", apptsSub: "Upcoming treatments booked by your agent.",
    calDim: "Calendar syncs live once Cal.com is connected.", upcoming: "Upcoming",
    settingsTitle: "Settings", tabs: { general: "General", voice: "Voice", booking: "Booking", faq: "FAQ" },
    locationInfo: "Location Info", testCall: "Test call", hours: "Hours", hoursSub: "When the clinic is open for appointments.",
    greetingMsgs: "Greeting Messages", openGreeting: "Open Hours Greeting", openGreetingSub: "Initial greeting during clinic hours.",
    closedGreeting: "Closed Hours Greeting", closedGreetingSub: "Greeting for calls outside clinic hours. It should clearly say the clinic is currently closed.",
    holidayHours: "Holiday Hours", holidayHoursSub: "Set special opening hours for holidays and events. The agent uses these automatically.",
    addHoliday: "Add Holiday", holidayName: "Holiday name", date: "Date", specialHours: "Special hours", closedAllDay: "Closed all day", save: "Save", remove: "Remove", upcomingLabel: "Upcoming", passedLabel: "Passed",
    tempClosure: "Temporary Closure", tempClosureSub: "Pause bookings for a break, holiday, or rush — the agent still answers calls.", setTempClosure: "Set Temporary Closure",
    selectVoice: "Select Voice", selectVoiceSub: "Choose the voice that represents your clinic.",
    voiceSpeed: "Voice Speed", voiceSpeedSub: "How slowly or quickly the agent speaks.",
    ambient: "Ambient Sound", ambientSub: "Subtle clinic ambience that makes calls feel natural.",
    faqTitle: "Frequently Asked Questions", faqSub: "Answers your agent gives callers automatically.", expandAll: "Expand all",
    bookingTitle: "Booking", bookingSub: "How the agent schedules appointments.",
    calcom: "Cal.com connection", calcomBody: "Bookings sync to the clinic's Google / Outlook calendar.",
    connected: "Connected", manage: "Manage",
    smsConfirm: "Send SMS confirmation", smsConfirmSub: "Text the patient once a booking is made.",
    smsRemind: "Send 24h reminder", smsRemindSub: "Remind the patient a day before their appointment.",
    slowest: "Slowest", normal: "Normal", fastest: "Fastest", quiet: "Quiet", loud: "Loud",
    khaleeji: "Arabic · Khaleeji", american: "Female · English", min: "min", sar: "SAR",
  },
  ar: {
    dir: "rtl", brandSub: "عيادة ديفينيا", active: "نشط — يستقبل المكالمات",
    greeting: "مساء الخير، ديفينيا", todayIs: "السبت، ٢:١٤ مساءً",
    earned: "لقد حجزت", earnedTail: "من العلاجات هذا الشهر",
    staffHours: "ساعات عمل تم توفيرها", thisMonth: "هذا الشهر",
    extraCalls: "مكالمات بعد ساعات العمل", bookings: "المواعيد المحجوزة",
    popular: "الأوقات المزدحمة اليوم", live: "الآن ٢ مساءً", optimize: "طوّر مساعدك",
    tipTitle: "فعّل الصوت العربي", tipBody: "معظم المتصلين في الرياض يفضلون العربية. فعّل الصوت النسائي الخليجي ليرحّب بهم بلغتهم.",
    configure: "إعداد", recent: "النشاط الأخير", recentSub: "أحدث المكالمات والرسائل والحجوزات في عيادتك.",
    viewAll: "عرض الكل", callCompleted: "اكتملت المكالمة", booked: "تم حجز موعد", msg: "رسالة واتساب",
    convosTitle: "المحادثات", convosSub: "كل مكالمة ومحادثة تعامل معها مساعدك.", searchConvos: "ابحث في المحادثات…",
    ordersOnly: "الحجوزات فقط", dateRange: "النطاق الزمني", apply: "تطبيق", cancel: "إلغاء",
    play: "تشغيل", sentiment: "المشاعر",
    servicesTitle: "الخدمات", servicesSub: "العلاجات التي يمكن لمساعدك تسعيرها وحجزها.", searchServices: "ابحث في العلاجات…",
    featured: "التوصيات المميزة", featuredSub: "يقترحها المساعد أثناء المكالمات حسب السياق.",
    addRec: "إضافة توصية", from: "من", book: "قابل للحجز", bookNow: "احجز موعداً",
    duration: "المدة", prep: "قبل زيارتك", aftercare: "بعد العلاج", tiers: "الخيارات والأسعار", about: "عن هذا العلاج",
    reportsTitle: "التقارير التفصيلية", reportsSub: "استكشف التحليلات والرؤى المعمّقة.",
    callAnalytics: "تحليلات المكالمات", callAnalyticsSub: "تعمّق في مقاييس المكالمات واتجاهاتها.",
    ordersRevenue: "الحجوزات والإيرادات", ordersRevenueSub: "حلّل حجم المواعيد والإيرادات.",
    totalCalls: "إجمالي المكالمات", totalCallsSub: "العدد الإجمالي للمكالمات",
    avgCalls: "متوسط المكالمات", avgCallsSub: "المتوسط اليومي", back: "رجوع",
    apptsTitle: "المواعيد", apptsSub: "العلاجات القادمة التي حجزها مساعدك.",
    calDim: "يتزامن التقويم مباشرة عند ربط Cal.com.", upcoming: "القادمة",
    settingsTitle: "الإعدادات", tabs: { general: "عام", voice: "الصوت", booking: "الحجز", faq: "الأسئلة الشائعة" },
    locationInfo: "معلومات الموقع", testCall: "مكالمة تجريبية", hours: "ساعات العمل", hoursSub: "أوقات فتح العيادة للمواعيد.",
    greetingMsgs: "رسائل الترحيب", openGreeting: "ترحيب أوقات العمل", openGreetingSub: "الترحيب الأولي خلال ساعات العيادة.",
    closedGreeting: "ترحيب خارج أوقات العمل", closedGreetingSub: "الترحيب للمكالمات خارج أوقات العيادة. يجب أن يوضّح أن العيادة مغلقة حالياً.",
    holidayHours: "ساعات العطلات", holidayHoursSub: "حدّد ساعات عمل خاصة للعطلات والمناسبات. يستخدمها المساعد تلقائياً.",
    addHoliday: "إضافة عطلة", holidayName: "اسم العطلة", date: "التاريخ", specialHours: "ساعات خاصة", closedAllDay: "مغلق طوال اليوم", save: "حفظ", remove: "حذف", upcomingLabel: "قادمة", passedLabel: "منتهية",
    tempClosure: "إغلاق مؤقت", tempClosureSub: "أوقف الحجوزات لاستراحة أو عطلة أو ازدحام — يستمر المساعد في الرد على المكالمات.", setTempClosure: "تعيين إغلاق مؤقت",
    selectVoice: "اختر الصوت", selectVoiceSub: "اختر الصوت الذي يمثّل عيادتك.",
    voiceSpeed: "سرعة الصوت", voiceSpeedSub: "مدى بطء أو سرعة حديث المساعد.",
    ambient: "الصوت المحيط", ambientSub: "أجواء عيادة خفيفة تجعل المكالمات طبيعية.",
    faqTitle: "الأسئلة الشائعة", faqSub: "الإجابات التي يقدّمها مساعدك للمتصلين تلقائياً.", expandAll: "توسيع الكل",
    bookingTitle: "الحجز", bookingSub: "كيف يحجز المساعد المواعيد.",
    calcom: "اتصال Cal.com", calcomBody: "تتزامن الحجوزات مع تقويم جوجل / آوتلوك للعيادة.",
    connected: "متصل", manage: "إدارة",
    smsConfirm: "إرسال تأكيد SMS", smsConfirmSub: "رسالة للمريض بمجرد تأكيد الحجز.",
    smsRemind: "تذكير قبل ٢٤ ساعة", smsRemindSub: "تذكير المريض قبل موعده بيوم.",
    slowest: "الأبطأ", normal: "عادي", fastest: "الأسرع", quiet: "هادئ", loud: "عالٍ",
    khaleeji: "عربي · خليجي", american: "أنثى · إنجليزي", min: "دقيقة", sar: "ريال",
  },
};

const SERVICES = [
  { id: "botox", en: "Botox", ar: "بوتوكس", cat: "Injectables", price: 900, dur: 30,
    about: { en: "A quick, precise injectable that relaxes targeted muscles to soften lines on the forehead, brows, and around the eyes. Results appear within 3–7 days.", ar: "حقن دقيق وسريع يرخي العضلات المستهدفة لتنعيم الخطوط على الجبهة والحاجبين وحول العينين. تظهر النتائج خلال ٣ إلى ٧ أيام." },
    tiers: [ { en: "1 area", ar: "منطقة واحدة", price: 900 }, { en: "2 areas", ar: "منطقتان", price: 1600 }, { en: "3 areas", ar: "٣ مناطق", price: 2200 } ],
    prep: { en: "Avoid blood thinners and alcohol 24h before. Arrive with a clean, makeup-free face.", ar: "تجنّب مميّعات الدم والكحول قبل ٢٤ ساعة. احضر بوجه نظيف خالٍ من المكياج." },
    after: { en: "Stay upright 4 hours, skip strenuous exercise for 24h, don't rub the area.", ar: "ابقَ منتصباً ٤ ساعات، تجنّب التمارين الشاقة ٢٤ ساعة، ولا تفرك المنطقة." } },
  { id: "filler", en: "Dermal Fillers", ar: "الفيلر الجلدي", cat: "Injectables", price: 1600, dur: 45,
    about: { en: "Hyaluronic-acid fillers restore volume and contour to lips, cheeks, and jawline. Results are immediate and last 9–12 months.", ar: "فيلر حمض الهيالورونيك يعيد الحجم والتحديد للشفاه والخدود وخط الفك. النتائج فورية وتدوم من ٩ إلى ١٢ شهراً." },
    tiers: [ { en: "Lip", ar: "الشفاه", price: 1600 }, { en: "Cheek", ar: "الخدود", price: 2100 }, { en: "Jawline", ar: "خط الفك", price: 2600 } ],
    prep: { en: "Avoid blood thinners 24h before. Tell us about any cold sores.", ar: "تجنّب مميّعات الدم قبل ٢٤ ساعة. أخبرنا بأي قرح باردة." },
    after: { en: "Mild swelling is normal for 48h. Apply ice, avoid heat and pressure.", ar: "التورّم الخفيف طبيعي لمدة ٤٨ ساعة. ضع الثلج وتجنّب الحرارة والضغط." } },
  { id: "hydra", en: "HydraFacial", ar: "هيدرافيشل", cat: "Facials", price: 650, dur: 50,
    about: { en: "A multi-step facial that cleanses, exfoliates, and hydrates with a gentle vortex system. No downtime, instant glow.", ar: "علاج متعدّد الخطوات ينظّف ويقشّر ويرطّب البشرة بنظام لطيف. بلا فترة نقاهة، ونضارة فورية." },
    tiers: [ { en: "Signature", ar: "الأساسي", price: 650 }, { en: "Deluxe", ar: "المطوّر", price: 900 }, { en: "Platinum", ar: "البلاتيني", price: 1200 } ],
    prep: { en: "Skip retinol and exfoliants 48h before. Come with clean skin.", ar: "تجنّب الريتينول والمقشّرات قبل ٤٨ ساعة. احضر ببشرة نظيفة." },
    after: { en: "Use SPF, avoid direct sun and saunas for 24h.", ar: "استخدم واقي الشمس وتجنّب الشمس المباشرة والساونا ٢٤ ساعة." } },
  { id: "laser", en: "Laser Hair Removal", ar: "إزالة الشعر بالليزر", cat: "Laser", price: 400, dur: 40,
    about: { en: "Diode laser targets hair follicles for lasting reduction. A course of 6–8 sessions gives the best results.", ar: "ليزر الدايود يستهدف بصيلات الشعر لتقليل دائم. جلسات من ٦ إلى ٨ تعطي أفضل النتائج." },
    tiers: [ { en: "Small area", ar: "منطقة صغيرة", price: 400 }, { en: "Medium area", ar: "منطقة متوسطة", price: 700 }, { en: "Full body", ar: "الجسم كامل", price: 1500 } ],
    prep: { en: "Shave the area 24h before. No waxing, tanning, or sun for 2 weeks prior.", ar: "احلق المنطقة قبل ٢٤ ساعة. تجنّب الشمع والتسمير والشمس لأسبوعين قبلها." },
    after: { en: "Avoid sun, hot showers, and gyms for 48h. Use SPF daily.", ar: "تجنّب الشمس والاستحمام الساخن والنوادي ٤٨ ساعة. استخدم واقي الشمس يومياً." } },
  { id: "prp", en: "PRP Hair Treatment", ar: "علاج الشعر بالبلازما", cat: "Restorative", price: 1200, dur: 60,
    about: { en: "Platelet-rich plasma from your own blood is injected into the scalp to stimulate hair growth over a course of sessions.", ar: "البلازما الغنية بالصفائح من دمك تُحقن في فروة الرأس لتحفيز نمو الشعر عبر عدة جلسات." },
    tiers: [ { en: "Single session", ar: "جلسة واحدة", price: 1200 }, { en: "Package of 3", ar: "باقة ٣ جلسات", price: 3200 } ],
    prep: { en: "Hydrate well and eat before your visit. Avoid blood thinners 3 days prior.", ar: "اشرب الماء وتناول الطعام قبل الزيارة. تجنّب مميّعات الدم ٣ أيام قبلها." },
    after: { en: "Don't wash hair for 6 hours. Avoid heat styling for 48h.", ar: "لا تغسل الشعر ٦ ساعات. تجنّب التصفيف الحراري ٤٨ ساعة." } },
  { id: "consult", en: "Skin Consultation", ar: "استشارة جلدية", cat: "Consultation", price: 200, dur: 20,
    about: { en: "A one-on-one assessment with a female dermatologist to map a personalized treatment plan for your skin.", ar: "تقييم فردي مع طبيبة جلدية لوضع خطة علاج مخصّصة لبشرتك." },
    tiers: [ { en: "Standard", ar: "عادية", price: 200 }, { en: "With skin analysis", ar: "مع تحليل البشرة", price: 350 } ],
    prep: { en: "Come with a clean face and a list of products you use.", ar: "احضري بوجه نظيف وقائمة بالمنتجات التي تستخدمينها." },
    after: { en: "You'll receive a written plan and quotes by SMS.", ar: "ستصلك خطة مكتوبة وعروض أسعار عبر SMS." } },
];

const CONVOS = [
  { name: "Nour A.", phone: "+966 55 214 8890", time: "2:02 PM", tag: "booked", lang: "ar",
    summary: "Caller asked to book Botox for next Tuesday. Agent offered morning or evening, confirmed 6:00 PM, sent an SMS confirmation and set a 24-hour reminder.",
    treatment: "Botox · 3 areas", price: 2200, sentiment: "Positive", dur: "01:12" },
  { name: "+966 50 771 3320", phone: "+966 50 771 3320", time: "1:37 PM", tag: "call", lang: "ar",
    summary: "Caller asked how long dermal filler lasts and whether a female doctor is available. Agent answered 9–12 months and confirmed a female doctor, then offered a consultation.",
    sentiment: "Positive", dur: "00:58" },
  { name: "Layla M.", phone: "+966 56 902 4471", time: "12:20 PM", tag: "msg", lang: "ar",
    summary: "WhatsApp: patient asked to reschedule Thursday's HydraFacial. Agent moved it to Saturday 5:00 PM and re-sent the confirmation.",
    sentiment: "Neutral", dur: "—" },
  { name: "Sara K.", phone: "+966 53 118 6642", time: "11:05 AM", tag: "call", lang: "en",
    summary: "English caller asked laser hair removal pricing and pre-treatment prep. Agent quoted 400 SAR/session and shared prep guidance, then booked a session for Sunday.",
    treatment: "Laser · 1 session", price: 400, sentiment: "Positive", dur: "02:03" },
  { name: "+966 59 440 1187", phone: "+966 59 440 1187", time: "10:41 AM", tag: "call", lang: "ar",
    summary: "Caller reported swelling after fillers and asked what to avoid. Agent flagged it as urgent and transferred to the on-call clinician.",
    sentiment: "Concerned", dur: "01:44", urgent: true },
];

const FAQS = [
  { en: "How do I book an appointment?", ar: "كيف أحجز موعداً؟", a_en: "You can book right over the phone or WhatsApp — the agent confirms instantly with an SMS.", a_ar: "يمكنك الحجز مباشرة عبر الهاتف أو واتساب، وسيؤكد المساعد موعدك فوراً برسالة SMS." },
  { en: "How much is Botox?", ar: "كم سعر البوتوكس؟", a_en: "Botox starts from SAR 900 per area.", a_ar: "يبدأ البوتوكس من ٩٠٠ ريال لكل منطقة." },
  { en: "How long do fillers last?", ar: "كم تدوم الفيلر؟", a_en: "Dermal fillers typically last 9–12 months.", a_ar: "تدوم الفيلر عادةً من ٩ إلى ١٢ شهراً." },
  { en: "Can I reschedule my appointment?", ar: "هل يمكنني تغيير موعدي؟", a_en: "Yes — just ask the agent and it will move your booking and re-send the confirmation.", a_ar: "نعم — فقط اطلب من المساعد وسيغيّر حجزك ويعيد إرسال التأكيد." },
  { en: "Do you have female doctors?", ar: "هل لديكم طبيبات؟", a_en: "Yes, female dermatologists are available on request.", a_ar: "نعم، تتوفّر طبيبات جلدية عند الطلب." },
  { en: "How should I prepare before laser?", ar: "كيف أستعد قبل الليزر؟", a_en: "Shave the area 24h before and avoid sun or tanning for two weeks prior.", a_ar: "احلق المنطقة قبل ٢٤ ساعة وتجنّب الشمس أو التسمير لأسبوعين قبلها." },
  { en: "What should I avoid after treatment?", ar: "ما الذي يجب تجنّبه بعد العلاج؟", a_en: "Avoid heat, direct sun, and strenuous exercise for 24–48 hours.", a_ar: "تجنّب الحرارة والشمس المباشرة والتمارين الشاقة لمدة ٢٤ إلى ٤٨ ساعة." },
];

const APPTS = [
  { name: "Nour A.", svc: { en: "Botox · 3 areas", ar: "بوتوكس · ٣ مناطق" }, day: { en: "Tue", ar: "الثلاثاء" }, date: "18", time: "6:00 PM", via: "AI · Voice" },
  { name: "Sara K.", svc: { en: "Laser Hair Removal", ar: "إزالة الشعر بالليزر" }, day: { en: "Sun", ar: "الأحد" }, date: "16", time: "3:30 PM", via: "AI · Voice" },
  { name: "Layla M.", svc: { en: "HydraFacial", ar: "هيدرافيشل" }, day: { en: "Sat", ar: "السبت" }, date: "15", time: "5:00 PM", via: "AI · WhatsApp" },
  { name: "Huda R.", svc: { en: "Skin Consultation", ar: "استشارة جلدية" }, day: { en: "Mon", ar: "الإثنين" }, date: "17", time: "2:00 PM", via: "AI · Voice" },
];

const HOLIDAYS = [
  { name: { en: "Saudi National Day", ar: "اليوم الوطني السعودي" }, date: { en: "Sep 23, 2026", ar: "٢٣ سبتمبر ٢٠٢٦" }, closed: true, hours: "", upcoming: true },
  { name: { en: "Eid al-Fitr", ar: "عيد الفطر" }, date: { en: "Mar 20, 2026", ar: "٢٠ مارس ٢٠٢٦" }, closed: false, hours: "4:00 PM → 9:00 PM", upcoming: false },
];

const VOL = [52,38,41,47,44,58,92,49,43,55,46,61,40,97,45,50,44,38,33,79,62,48,52,41,58,33,120,64];

const REPORTS = {
  call: [
    { id: "volume", en: "Call Volume Trends", ar: "اتجاهات حجم المكالمات", chart: "line", desc_en: "Number of calls received over time", desc_ar: "عدد المكالمات المستلمة عبر الوقت" },
    { id: "duration", en: "Call Duration Breakdown", ar: "تحليل مدة المكالمات", chart: "bar", desc_en: "How long calls typically last", desc_ar: "المدة المعتادة للمكالمات" },
    { id: "sentiment", en: "Average Sentiment", ar: "متوسط المشاعر", chart: "donut", desc_en: "Caller mood across conversations", desc_ar: "مشاعر المتصلين عبر المحادثات" },
    { id: "peak", en: "Peak Hours Analysis", ar: "تحليل ساعات الذروة", chart: "bar", desc_en: "Busiest hours of the day", desc_ar: "أكثر ساعات اليوم ازدحاماً" },
    { id: "afterhours", en: "After-Hours Calls Served", ar: "مكالمات بعد ساعات العمل", chart: "line", desc_en: "Calls the agent captured while closed", desc_ar: "المكالمات التي التقطها المساعد بعد الإغلاق" },
  ],
  orders: [
    { id: "bookvol", en: "Booking Volume Trends", ar: "اتجاهات حجم الحجوزات", chart: "line", desc_en: "Appointments booked over time", desc_ar: "المواعيد المحجوزة عبر الوقت" },
    { id: "revenue", en: "Revenue Trends", ar: "اتجاهات الإيرادات", chart: "line", desc_en: "Treatment revenue over time", desc_ar: "إيرادات العلاجات عبر الوقت" },
    { id: "bytreatment", en: "Bookings by Treatment", ar: "الحجوزات حسب العلاج", chart: "hbar", desc_en: "Which treatments book the most", desc_ar: "أكثر العلاجات حجزاً" },
    { id: "channel", en: "Booking Channel Split", ar: "قنوات الحجز", chart: "donut", desc_en: "Voice vs WhatsApp vs web", desc_ar: "الصوت مقابل واتساب مقابل الويب" },
  ],
};

const Card = ({ children, style }) => (
  <div style={{ background: C.card, borderRadius: 24, boxShadow: "0 1px 2px rgba(27,36,49,.04), 0 8px 24px rgba(27,36,49,.05)", ...style }}>{children}</div>
);
const Pill = ({ children, bg, fg, style }) => (
  <span style={{ background: bg, color: fg, padding: "5px 12px", borderRadius: 999, fontSize: 12.5, fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 6, whiteSpace: "nowrap", ...style }}>{children}</span>
);
const IconBox = ({ children, bg, fg }) => (
  <div style={{ width: 46, height: 46, borderRadius: 14, background: bg, color: fg, display: "grid", placeItems: "center", flexShrink: 0 }}>{children}</div>
);

export default function App() {
  const [lang, setLang] = useState("en");
  const [nav, setNav] = useState("overview");
  const [drawer, setDrawer] = useState(false);
  const [tab, setTab] = useState("general");
  const [openFaq, setOpenFaq] = useState(0);
  const [branchOpen, setBranchOpen] = useState(false);
  const [branch, setBranch] = useState(BRANCHES[0]);
  const [svcOpen, setSvcOpen] = useState(null);
  const [reportOpen, setReportOpen] = useState(null);
  const t = T[lang];
  const rtl = lang === "ar";
  const money = (n) => rtl ? `${n.toLocaleString("ar-EG")} ${t.sar}` : `${t.sar} ${n.toLocaleString()}`;

  const NAV = [["overview", Home], ["convos", Phone], ["services", Sparkles], ["reports", PieChart], ["appts", Calendar], ["settings", SettingsIcon], ["support", HelpCircle]];
  const go = (k) => { setNav(k); setDrawer(false); setSvcOpen(null); setReportOpen(null); };

  return (
    <div dir={t.dir} style={{ fontFamily: rtl ? "'Segoe UI','Noto Sans Arabic',Tahoma,sans-serif" : "'Poppins','Segoe UI',system-ui,sans-serif", background: C.bg, minHeight: "100vh", color: C.ink }}>

      <div style={{ position: "sticky", top: 0, zIndex: 40, background: C.card, borderBottom: `1px solid ${C.line}`, padding: "12px 16px", display: "flex", alignItems: "center", gap: 12 }}>
        <button onClick={() => setDrawer(true)} style={{ width: 44, height: 44, borderRadius: 999, background: C.cardAlt, border: "none", display: "grid", placeItems: "center", cursor: "pointer", flexShrink: 0 }}>
          <MenuIcon size={20} color={C.ink} />
        </button>
        <div style={{ flex: 1, position: "relative" }}>
          <button onClick={() => setBranchOpen(o => !o)} style={{ width: "100%", background: C.cardAlt, borderRadius: 999, padding: "12px 18px", fontWeight: 700, fontSize: 15, display: "flex", alignItems: "center", justifyContent: "space-between", border: "none", cursor: "pointer", color: C.ink, overflow: "hidden" }}>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{branch.name[lang]}</span>
            <ChevronDown size={18} color={C.sub} style={{ transform: branchOpen ? "rotate(180deg)" : "none", transition: ".2s", flexShrink: 0 }} />
          </button>
          {branchOpen && (
            <>
              <div onClick={() => setBranchOpen(false)} style={{ position: "fixed", inset: 0, zIndex: 41 }} />
              <div style={{ position: "absolute", top: 54, left: 0, right: 0, zIndex: 42, background: C.card, borderRadius: 20, boxShadow: "0 12px 40px rgba(27,36,49,.18)", overflow: "hidden" }}>
                {BRANCHES.map((b, i) => {
                  const on = b.id === branch.id;
                  return (
                    <button key={b.id} onClick={() => { setBranch(b); setBranchOpen(false); }} style={{ width: "100%", textAlign: rtl ? "right" : "left", background: on ? C.amberSoft : "transparent", border: "none", borderTop: i ? `1px solid ${C.line}` : "none", padding: "16px 18px", cursor: "pointer", display: "flex", gap: 12, alignItems: "flex-start" }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                          <span style={{ fontWeight: 800, fontSize: 15, color: C.ink }}>{b.name[lang]}</span>
                          <Pill bg={C.greenSoft} fg={C.green} style={{ fontSize: 10.5, padding: "3px 9px" }}>{rtl ? "نشط" : "Active"}</Pill>
                        </div>
                        <div style={{ color: C.sub, fontSize: 13, lineHeight: 1.4 }}>{b.addr[lang]}</div>
                      </div>
                      {on && <Check size={20} color={C.ink} style={{ flexShrink: 0, marginTop: 2 }} />}
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>
        <button onClick={() => setLang(rtl ? "en" : "ar")} style={{ height: 44, padding: "0 14px", borderRadius: 999, background: C.blueSoft, color: C.blueDeep, border: "none", fontWeight: 800, fontSize: 14, display: "inline-flex", alignItems: "center", gap: 7, cursor: "pointer", flexShrink: 0 }}>
          <Globe size={17} /> {rtl ? "EN" : "ع"}
        </button>
      </div>

      {drawer && (
        <div onClick={() => setDrawer(false)} style={{ position: "fixed", inset: 0, zIndex: 50, background: "rgba(27,36,49,.42)" }}>
          <div onClick={e => e.stopPropagation()} style={{ position: "absolute", top: 0, bottom: 0, [rtl ? "right" : "left"]: 0, width: 300, maxWidth: "85%", background: C.card, padding: 20, display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <Brand /><button onClick={() => setDrawer(false)} style={{ border: "none", background: "transparent", cursor: "pointer" }}><X size={22} color={C.ink} /></button>
            </div>
            {NAV.map(([k, Ic]) => {
              const on = nav === k;
              return (
                <button key={k} onClick={() => go(k)} style={{ display: "flex", alignItems: "center", gap: 14, padding: "13px 14px", borderRadius: 14, border: "none", cursor: "pointer", background: on ? C.blueSoft : "transparent", color: on ? C.blueDeep : C.ink, fontWeight: on ? 800 : 600, fontSize: 16, textAlign: rtl ? "right" : "left" }}>
                  <Ic size={21} color={on ? C.blueDeep : C.sub} /> {navLabel(t, k)}
                  {k === "services" && <Pill bg={C.greenSoft} fg={C.green} style={{ [rtl ? "marginRight" : "marginLeft"]: "auto", fontSize: 11 }}><Sparkles size={12} /> New</Pill>}
                </button>
              );
            })}
            <div style={{ marginTop: "auto" }}>
              <div style={{ background: C.greenSoft, borderRadius: 14, padding: "13px 16px", display: "flex", alignItems: "center", gap: 10, fontWeight: 800, fontSize: 15 }}>
                <span style={{ width: 10, height: 10, borderRadius: 999, background: C.green }} /> {t.active}
                <Pause size={16} color={C.amber} style={{ [rtl ? "marginRight" : "marginLeft"]: "auto" }} />
              </div>
              <div style={{ marginTop: 10, background: C.cardAlt, borderRadius: 14, padding: "12px 14px", display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 40, height: 40, borderRadius: 999, background: `linear-gradient(135deg,${C.blue},${C.blueDeep})`, display: "grid", placeItems: "center", color: "#fff", fontWeight: 800 }}>D</div>
                <div style={{ overflow: "hidden" }}>
                  <div style={{ fontWeight: 800, fontSize: 14, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{branch.name[lang]}</div>
                  <div style={{ color: C.sub, fontSize: 12.5 }}>{rtl ? "السعودية" : "Saudi Arabia"}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div style={{ maxWidth: 640, margin: "0 auto", padding: 16 }}>
        {nav === "overview" && <Overview t={t} rtl={rtl} money={money} go={go} />}
        {nav === "convos" && <Convos t={t} rtl={rtl} money={money} lang={lang} />}
        {nav === "services" && (svcOpen
          ? <ServiceDetail t={t} rtl={rtl} money={money} lang={lang} svc={SERVICES.find(s => s.id === svcOpen)} onBack={() => setSvcOpen(null)} />
          : <Services t={t} rtl={rtl} money={money} lang={lang} onOpen={setSvcOpen} />)}
        {nav === "reports" && (reportOpen
          ? <ReportDetail t={t} rtl={rtl} lang={lang} report={reportOpen} onBack={() => setReportOpen(null)} money={money} />
          : <Reports t={t} rtl={rtl} lang={lang} onOpen={setReportOpen} />)}
        {nav === "appts" && <Appts t={t} rtl={rtl} lang={lang} />}
        {nav === "settings" && <SettingsPage t={t} rtl={rtl} tab={tab} setTab={setTab} openFaq={openFaq} setOpenFaq={setOpenFaq} lang={lang} branch={branch} />}
        {nav === "support" && <Support t={t} />}
      </div>
    </div>
  );
}

function navLabel(t, k) {
  const map = { overview: { en: "Overview", ar: "الرئيسية" }, convos: { en: "Conversations", ar: "المحادثات" }, services: { en: "Services", ar: "الخدمات" }, reports: { en: "Reports", ar: "التقارير" }, appts: { en: "Appointments", ar: "المواعيد" }, settings: { en: "Settings", ar: "الإعدادات" }, support: { en: "Support", ar: "الدعم" } };
  return t.dir === "rtl" ? map[k].ar : map[k].en;
}

function Brand() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
      <div style={{ width: 34, height: 34, borderRadius: 10, background: `linear-gradient(135deg,${C.blue},${C.blueDeep})`, display: "grid", placeItems: "center", color: "#fff", fontWeight: 900, fontSize: 20, fontFamily: "system-ui" }}>A</div>
      <div style={{ fontWeight: 900, fontSize: 20, letterSpacing: -0.4 }}>Atlas<span style={{ color: C.blue }}>Prime</span><span style={{ color: C.blueDeep }}>X</span></div>
    </div>
  );
}

function Overview({ t, rtl, money, go }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ padding: "8px 4px" }}>
        <h1 style={{ fontSize: 30, fontWeight: 900, margin: "6px 0 10px", letterSpacing: -0.5 }}>{t.greeting}</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: C.sub, fontWeight: 600, marginBottom: 14 }}><Clock size={17} /> {t.todayIs}</div>
        <div style={{ fontSize: 27, fontWeight: 800 }}>{t.earned} <span style={{ color: C.blue }}>{money(184500)}</span> {t.earnedTail}</div>
      </div>
      <Kpi icon={<Clock size={22} />} bg={C.blueSoft} fg={C.blue} label={t.staffHours} value={rtl ? "٣٤ ساعة" : "34 hours"} sub={t.thisMonth} />
      <Kpi icon={<PhoneIncoming size={22} />} bg={C.amberSoft} fg={C.amber} label={t.extraCalls} value={rtl ? "١١٨" : "118"} sub={t.thisMonth} />
      <Kpi icon={<CalendarCheck size={22} />} bg={C.greenSoft} fg={C.green} label={t.bookings} value={rtl ? "٢٤٣" : "243"} sub={t.thisMonth} />
      <Card style={{ padding: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <h2 style={{ fontSize: 22, fontWeight: 900, margin: 0 }}>{t.popular}</h2>
          <Pill bg={C.cardAlt} fg={C.ink}>{rtl ? "السبت" : "Saturday"}</Pill>
        </div>
        <Pill bg={C.amberSoft} fg={C.amber} style={{ marginBottom: 22 }}>{t.live}</Pill>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 10, height: 90, marginBottom: 8 }}>
          {[30,44,72,90,64,52,40,34,30].map((h, i) => <div key={i} style={{ flex: 1, height: h, borderRadius: "10px 10px 4px 4px", background: i === 3 ? C.blue : i < 3 ? C.ink : C.line }} />)}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", color: C.sub, fontSize: 13, fontWeight: 600 }}><span>1PM</span><span>4PM</span><span>7PM</span><span>9PM</span></div>
      </Card>
      <div style={{ color: C.sub, fontWeight: 700, fontSize: 15, padding: "2px 6px" }}>{t.optimize}</div>
      <Card style={{ padding: 20 }}>
        <div style={{ display: "flex", gap: 14 }}>
          <IconBox bg={C.blueSoft} fg={C.blue}><Sparkles size={22} /></IconBox>
          <div>
            <h3 style={{ margin: "2px 0 6px", fontSize: 18, fontWeight: 800 }}>{t.tipTitle}</h3>
            <p style={{ margin: "0 0 12px", color: C.sub, lineHeight: 1.5 }}>{t.tipBody}</p>
            <button onClick={() => go("settings")} style={{ background: "transparent", border: "none", color: C.blue, fontWeight: 800, fontSize: 15, cursor: "pointer", padding: 0 }}>{t.configure} →</button>
          </div>
        </div>
      </Card>
      <Card style={{ padding: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
          <div><h2 style={{ fontSize: 22, fontWeight: 900, margin: "0 0 6px" }}>{t.recent}</h2><p style={{ margin: 0, color: C.sub, maxWidth: 320, lineHeight: 1.45 }}>{t.recentSub}</p></div>
          <button onClick={() => go("convos")} style={{ background: C.blueSoft, color: C.blueDeep, border: "none", borderRadius: 999, padding: "10px 16px", fontWeight: 800, cursor: "pointer", whiteSpace: "nowrap" }}>{t.viewAll}</button>
        </div>
        <div style={{ marginTop: 12 }}>
          {[
            { icon: <CalendarCheck size={20} />, bg: C.greenSoft, fg: C.green, title: "Nour A.", meta: `${t.booked} · ${rtl ? "قبل ١٢ دقيقة" : "12 min ago"}`, right: money(2200) },
            { icon: <Phone size={20} />, bg: C.cardAlt, fg: C.sub, title: "+966 50 771 3320", meta: `${t.callCompleted} · ${rtl ? "قبل ٤٠ دقيقة" : "40 min ago"}`, right: "" },
            { icon: <MessageSquare size={20} />, bg: C.blueSoft, fg: C.blue, title: "Layla M.", meta: `${t.msg} · ${rtl ? "قبل ساعة" : "1 hr ago"}`, right: "" },
            { icon: <Phone size={20} />, bg: C.cardAlt, fg: C.sub, title: "Sara K.", meta: `${t.callCompleted} · ${rtl ? "قبل ٣ ساعات" : "3 hrs ago"}`, right: money(400) },
          ].map((r, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 0", borderTop: i ? `1px solid ${C.line}` : "none" }}>
              <IconBox bg={r.bg} fg={r.fg}>{r.icon}</IconBox>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 800, fontSize: 16 }}>{r.title}</div>
                <div style={{ color: C.sub, fontSize: 13.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.meta}</div>
              </div>
              {r.right && <div style={{ fontWeight: 900, color: C.green, fontSize: 17 }}>{r.right}</div>}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function Kpi({ icon, bg, fg, label, value, sub }) {
  return (
    <Card style={{ padding: 22 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18 }}>
        <div style={{ color: C.sub, fontWeight: 700, fontSize: 15 }}>{label}</div>
        <IconBox bg={bg} fg={fg}>{icon}</IconBox>
      </div>
      <div style={{ fontSize: 40, fontWeight: 900, letterSpacing: -1, lineHeight: 1 }}>{value}</div>
      <div style={{ color: C.sub, marginTop: 8, fontWeight: 600 }}>{sub}</div>
    </Card>
  );
}

function Convos({ t, rtl, money, lang }) {
  const [q, setQ] = useState("");
  const [showCal, setShowCal] = useState(false);
  const list = CONVOS.filter(c => !q || c.name.toLowerCase().includes(q.toLowerCase()));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Header title={t.convosTitle} sub={t.convosSub} />
      <div style={{ position: "relative" }}>
        <Search size={20} color={C.sub} style={{ position: "absolute", top: 16, [rtl ? "right" : "left"]: 16 }} />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder={t.searchConvos} style={{ width: "100%", boxSizing: "border-box", padding: rtl ? "15px 48px 15px 16px" : "15px 16px 15px 48px", borderRadius: 16, border: "none", background: C.card, fontSize: 15, color: C.ink, outline: "none", fontFamily: "inherit" }} />
      </div>
      <div style={{ display: "flex", gap: 10 }}>
        <Pill bg={C.card} fg={C.ink} style={{ padding: "11px 16px", fontSize: 14 }}><CalendarCheck size={16} /> {t.ordersOnly}</Pill>
        <button onClick={() => setShowCal(true)} style={{ background: C.card, border: "none", borderRadius: 999, padding: "11px 16px", fontSize: 14, fontWeight: 700, color: C.ink, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6, fontFamily: "inherit" }}>
          <Calendar size={16} /> {t.dateRange} <ChevronDown size={15} />
        </button>
      </div>
      {list.map((c, i) => <ConvoCard key={i} c={c} t={t} rtl={rtl} money={money} />)}
      {showCal && <DatePicker t={t} rtl={rtl} onClose={() => setShowCal(false)} />}
    </div>
  );
}

function DatePicker({ t, rtl, onClose }) {
  const days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
  const daysAr = ["أحد","إثنين","ثلاثاء","أربعاء","خميس","جمعة","سبت"];
  const grid = [];
  const leading = [28,29,30];
  let n = 1;
  for (let i = 0; i < 35; i++) {
    if (i < 3) grid.push({ d: leading[i], dim: true });
    else if (n <= 31) grid.push({ d: n++, dim: false });
    else grid.push({ d: n++ - 31, dim: true });
  }
  const inRange = (d) => d >= 17 && d <= 24;
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 60, background: "rgba(27,36,49,.42)", display: "grid", placeItems: "center", padding: 20 }}>
      <div onClick={e => e.stopPropagation()} style={{ background: C.card, borderRadius: 24, padding: 20, width: "100%", maxWidth: 380 }}>
        <div style={{ display: "flex", gap: 10, background: C.cardAlt, padding: 6, borderRadius: 14, marginBottom: 18 }}>
          <div style={{ flex: 1, background: C.card, border: `1.5px solid ${C.blue}`, borderRadius: 10, padding: "12px", textAlign: "center", fontWeight: 800 }}>{rtl ? "١٧ يوليو ٢٠٢٦" : "Jul 17, 2026"}</div>
          <div style={{ flex: 1, background: C.card, borderRadius: 10, padding: "12px", textAlign: "center", fontWeight: 800, color: C.sub }}>{rtl ? "٢٤ يوليو ٢٠٢٦" : "Jul 24, 2026"}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <button style={arrowBtn}>{rtl ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}</button>
          <div style={{ fontWeight: 800, fontSize: 17 }}>{rtl ? "يوليو ٢٠٢٦" : "July 2026"}</div>
          <button style={arrowBtn}>{rtl ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}</button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 2, marginBottom: 6 }}>
          {(rtl ? daysAr : days).map(d => <div key={d} style={{ textAlign: "center", color: C.sub, fontSize: 12, fontWeight: 700, padding: "4px 0" }}>{d}</div>)}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 2 }}>
          {grid.map((c, i) => {
            const sel = !c.dim && inRange(c.d);
            const edge = !c.dim && (c.d === 17 || c.d === 24);
            return (
              <div key={i} style={{ textAlign: "center", padding: "10px 0", borderRadius: sel ? 999 : 0, background: sel ? C.amber : "transparent", color: c.dim ? "#CFC7B8" : sel ? "#fff" : C.ink, fontWeight: edge ? 800 : 600, fontSize: 15 }}>{c.d}</div>
            );
          })}
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 18 }}>
          <button onClick={onClose} style={{ background: C.cardAlt, border: "none", borderRadius: 999, padding: "12px 24px", fontWeight: 800, cursor: "pointer", color: C.ink, fontFamily: "inherit" }}>{t.cancel}</button>
          <button onClick={onClose} style={{ background: C.amber, border: "none", borderRadius: 999, padding: "12px 28px", fontWeight: 800, cursor: "pointer", color: "#fff", fontFamily: "inherit" }}>{t.apply}</button>
        </div>
      </div>
    </div>
  );
}
const arrowBtn = { width: 40, height: 40, borderRadius: 12, background: C.cardAlt, border: "none", display: "grid", placeItems: "center", cursor: "pointer", color: C.ink };

function ConvoCard({ c, t, rtl, money }) {
  const [open, setOpen] = useState(c.tag === "booked");
  const tagMap = {
    booked: { bg: C.greenSoft, fg: C.green, icon: <CalendarCheck size={15} /> },
    call: { bg: C.cardAlt, fg: C.sub, icon: <Phone size={15} /> },
    msg: { bg: C.blueSoft, fg: C.blue, icon: <MessageSquare size={15} /> },
  }[c.tag];
  return (
    <Card style={{ padding: 18, border: c.urgent ? `1.5px solid ${C.rose}` : "none" }}>
      <div onClick={() => setOpen(o => !o)} style={{ display: "flex", alignItems: "center", gap: 14, cursor: "pointer" }}>
        <IconBox bg={tagMap.bg} fg={tagMap.fg}>{tagMap.icon}</IconBox>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 800, fontSize: 16, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{c.name}</div>
          <div style={{ color: C.sub, fontSize: 13 }}>{c.phone} · {c.time}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Pill bg={c.lang === "ar" ? C.blueSoft : C.cardAlt} fg={c.lang === "ar" ? C.blueDeep : C.sub} style={{ fontSize: 11 }}>{c.lang === "ar" ? "ع" : "EN"}</Pill>
          <ChevronDown size={20} color={C.sub} style={{ transform: open ? "rotate(180deg)" : "none", transition: ".2s" }} />
        </div>
      </div>
      {open && (
        <div style={{ marginTop: 14 }}>
          {c.treatment && (
            <div style={{ background: C.greenSoft, borderRadius: 16, padding: 16, display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div style={{ fontWeight: 800 }}>{c.treatment}</div><div style={{ fontWeight: 900, color: C.green }}>{money(c.price)}</div>
            </div>
          )}
          {c.urgent && <Pill bg={C.amberSoft} fg={C.amber} style={{ marginBottom: 12 }}><AlertTriangle size={14} /> {rtl ? "تم التحويل — عاجل" : "Transferred · Urgent"}</Pill>}
          <p style={{ color: C.sub, lineHeight: 1.6, margin: "0 0 14px", fontSize: 15 }}>{c.summary}</p>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <button style={btnDark}><Play size={16} /> {t.play} {c.dur !== "—" && `(${c.dur})`}</button>
            <Pill bg={C.cardAlt} fg={C.ink} style={{ padding: "10px 14px" }}>{t.sentiment}: {c.sentiment}</Pill>
          </div>
        </div>
      )}
    </Card>
  );
}

function Services({ t, rtl, money, lang, onOpen }) {
  const [q, setQ] = useState("");
  const cats = [...new Set(SERVICES.map(s => s.cat))];
  const list = SERVICES.filter(s => !q || (lang === "ar" ? s.ar : s.en).includes(q));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Header title={t.servicesTitle} sub={t.servicesSub} />
      <div style={{ position: "relative" }}>
        <Search size={20} color={C.sub} style={{ position: "absolute", top: 16, [rtl ? "right" : "left"]: 16 }} />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder={t.searchServices} style={{ width: "100%", boxSizing: "border-box", padding: rtl ? "15px 48px 15px 16px" : "15px 16px 15px 48px", borderRadius: 16, border: "none", background: C.card, fontSize: 15, outline: "none", fontFamily: "inherit", color: C.ink }} />
      </div>
      <div style={{ display: "flex", gap: 22, borderBottom: `1px solid ${C.line}`, paddingBottom: 4, overflowX: "auto" }}>
        {cats.map((cat, i) => <div key={cat} style={{ fontWeight: 800, fontSize: 15, color: i === 0 ? C.ink : C.sub, whiteSpace: "nowrap", paddingBottom: 8, borderBottom: i === 0 ? `2px solid ${C.blue}` : "none" }}>{cat} <span style={{ color: C.sub, fontWeight: 600 }}>({SERVICES.filter(s => s.cat === cat).length})</span></div>)}
      </div>
      <Card style={{ padding: 20 }}>
        <div style={{ display: "flex", gap: 14, marginBottom: 14 }}>
          <IconBox bg={C.greenSoft} fg={C.green}><ArrowUpRight size={22} /></IconBox>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}><h3 style={{ margin: 0, fontSize: 18, fontWeight: 900 }}>{t.featured}</h3><Pill bg={C.cardAlt} fg={C.sub} style={{ fontSize: 11 }}>2/5</Pill></div>
            <p style={{ margin: "6px 0 0", color: C.sub, lineHeight: 1.45 }}>{t.featuredSub}</p>
          </div>
        </div>
        <button style={{ width: "100%", background: C.cardAlt, border: "none", borderRadius: 14, padding: 14, fontWeight: 800, fontSize: 15, color: C.ink, cursor: "pointer", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, fontFamily: "inherit" }}><Plus size={18} /> {t.addRec}</button>
      </Card>
      {list.map(s => (
        <Card key={s.id} style={{ padding: 20 }}>
          <div onClick={() => onOpen(s.id)} style={{ cursor: "pointer" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ fontWeight: 800, fontSize: 18, marginBottom: 4 }}>{lang === "ar" ? s.ar : s.en}</div>
              <ChevronDown size={20} color={C.sub} style={{ transform: rtl ? "rotate(90deg)" : "rotate(-90deg)" }} />
            </div>
            <div style={{ color: C.sub, fontSize: 14, marginBottom: 12 }}>{s.cat} · {s.dur} {t.min}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontWeight: 900, fontSize: 19 }}>{t.from} {money(s.price)}</span>
              <Pill bg={C.greenSoft} fg={C.green} style={{ fontSize: 12, [rtl ? "marginRight" : "marginLeft"]: "auto" }}><CheckCircle2 size={13} /> {t.book}</Pill>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

function ServiceDetail({ t, rtl, money, lang, svc, onBack }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <button onClick={onBack} style={backBtn}>{rtl ? <ChevronRight size={18} /> : <ArrowLeft size={18} />} {t.back}</button>
      <div>
        <h1 style={{ fontSize: 28, fontWeight: 900, margin: "0 0 8px" }}>{lang === "ar" ? svc.ar : svc.en}</h1>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Pill bg={C.blueSoft} fg={C.blueDeep}>{svc.cat}</Pill>
          <Pill bg={C.cardAlt} fg={C.ink}><Timer size={14} /> {svc.dur} {t.min}</Pill>
          <Pill bg={C.greenSoft} fg={C.green}><CheckCircle2 size={13} /> {t.book}</Pill>
        </div>
      </div>
      <Card style={{ padding: 22 }}>
        <div style={{ fontWeight: 900, fontSize: 16, marginBottom: 10 }}>{t.about}</div>
        <p style={{ margin: 0, color: C.sub, lineHeight: 1.65, fontSize: 15 }}>{lang === "ar" ? svc.about.ar : svc.about.en}</p>
      </Card>
      <Card style={{ padding: 22 }}>
        <div style={{ fontWeight: 900, fontSize: 16, marginBottom: 14 }}>{t.tiers}</div>
        {svc.tiers.map((tr, i) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 0", borderTop: i ? `1px solid ${C.line}` : "none" }}>
            <span style={{ fontWeight: 700, fontSize: 16 }}>{lang === "ar" ? tr.ar : tr.en}</span>
            <span style={{ fontWeight: 900, fontSize: 17, color: C.blue }}>{money(tr.price)}</span>
          </div>
        ))}
      </Card>
      <InfoCard icon={<ShieldCheck size={20} />} bg={C.blueSoft} fg={C.blue} title={t.prep} body={lang === "ar" ? svc.prep.ar : svc.prep.en} />
      <InfoCard icon={<Smile size={20} />} bg={C.greenSoft} fg={C.green} title={t.aftercare} body={lang === "ar" ? svc.after.ar : svc.after.en} />
      <button style={{ background: C.blue, color: "#fff", border: "none", borderRadius: 999, padding: "16px", fontWeight: 800, fontSize: 16, cursor: "pointer", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, fontFamily: "inherit", boxShadow: `0 8px 20px ${C.blue}44` }}>
        <CalendarCheck size={19} /> {t.bookNow}
      </button>
    </div>
  );
}
function InfoCard({ icon, bg, fg, title, body }) {
  return (
    <Card style={{ padding: 20 }}>
      <div style={{ display: "flex", gap: 12 }}>
        <IconBox bg={bg} fg={fg}>{icon}</IconBox>
        <div><div style={{ fontWeight: 800, fontSize: 16, marginBottom: 4 }}>{title}</div><p style={{ margin: 0, color: C.sub, lineHeight: 1.55, fontSize: 14.5 }}>{body}</p></div>
      </div>
    </Card>
  );
}

function Reports({ t, rtl, lang, onOpen }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Header title={t.reportsTitle} sub={t.reportsSub} />
      <ReportGroup t={t} lang={lang} icon={<PhoneCall size={22} />} bg={C.amberSoft} fg={C.amber} title={t.callAnalytics} sub={t.callAnalyticsSub} items={REPORTS.call} onOpen={onOpen} />
      <ReportGroup t={t} lang={lang} icon={<TrendingUp size={22} />} bg={C.greenSoft} fg={C.green} title={t.ordersRevenue} sub={t.ordersRevenueSub} items={REPORTS.orders} onOpen={onOpen} />
    </div>
  );
}
function ReportGroup({ t, lang, icon, bg, fg, title, sub, items, onOpen }) {
  return (
    <Card style={{ padding: 22 }}>
      <div style={{ display: "flex", gap: 14, marginBottom: 12 }}>
        <IconBox bg={bg} fg={fg}>{icon}</IconBox>
        <div><h3 style={{ margin: "2px 0 4px", fontSize: 19, fontWeight: 900 }}>{title}</h3><p style={{ margin: 0, color: C.sub }}>{sub}</p></div>
      </div>
      {items.map((r, i) => (
        <div key={r.id} onClick={() => onOpen(r)} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 0", borderTop: i ? `1px solid ${C.line}` : "none", cursor: "pointer" }}>
          <span style={{ fontWeight: 700, fontSize: 16 }}>{lang === "ar" ? r.ar : r.en}</span>
          <ArrowUpRight size={20} color={C.blue} />
        </div>
      ))}
    </Card>
  );
}

function ReportDetail({ t, rtl, lang, report, onBack, money }) {
  const title = lang === "ar" ? report.ar : report.en;
  const desc = lang === "ar" ? report.desc_ar : report.desc_en;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <button onClick={onBack} style={backBtn}>{rtl ? <ChevronRight size={18} /> : <ArrowLeft size={18} />} {t.back}</button>
      <div>
        <h1 style={{ fontSize: 27, fontWeight: 900, margin: "0 0 6px", letterSpacing: -0.5 }}>{title}</h1>
        <p style={{ margin: 0, color: C.sub }}>{desc}</p>
      </div>
      <Card style={{ padding: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <Pill bg={C.cardAlt} fg={C.ink}><Calendar size={14} /> {rtl ? "١٧ يونيو – ١٧ يوليو" : "Jun 17 – Jul 17"}</Pill>
        </div>
        <ChartFor type={report.chart} rtl={rtl} />
      </Card>
      <StatsFor report={report} t={t} rtl={rtl} money={money} />
    </div>
  );
}

function ChartFor({ type, rtl }) {
  if (type === "line") return <LineChart data={VOL} />;
  if (type === "bar") return <BarChart data={[22,38,54,61,48,33,26]} labels={rtl ? ["٩ص","١١ص","١م","٣م","٥م","٧م","٩م"] : ["9a","11a","1p","3p","5p","7p","9p"]} />;
  if (type === "hbar") return <HBarChart rows={[["HydraFacial",84],["Botox",71],["Laser",58],["Filler",44],["PRP",22],["Consult",19]]} />;
  if (type === "donut") return <DonutChart segments={[[62,C.green],[26,C.blue],[12,C.amber]]} labels={rtl ? ["إيجابي","محايد","قلق"] : ["Positive","Neutral","Concerned"]} />;
  return <LineChart data={VOL} />;
}
function LineChart({ data }) {
  const max = Math.max(...data);
  return (
    <svg viewBox="0 0 320 150" style={{ width: "100%", height: 160 }} preserveAspectRatio="none">
      {[0,37,74,111,148].map(y => <line key={y} x1="0" x2="320" y1={y} y2={y} stroke={C.line} strokeWidth="1" strokeDasharray="4 4" />)}
      <polygon fill="url(#lg)" opacity="0.18" points={`0,150 ${data.map((v, i) => `${(i/(data.length-1))*320},${150-(v/max)*138}`).join(" ")} 320,150`} />
      <polyline fill="none" stroke={C.blue} strokeWidth="2.5" strokeLinejoin="round" points={data.map((v, i) => `${(i/(data.length-1))*320},${150-(v/max)*138}`).join(" ")} />
      <defs><linearGradient id="lg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={C.blue} /><stop offset="1" stopColor={C.blue} stopOpacity="0" /></linearGradient></defs>
    </svg>
  );
}
function BarChart({ data, labels }) {
  const max = Math.max(...data);
  const maxIdx = data.indexOf(max);
  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 150 }}>
        {data.map((v, i) => <div key={i} style={{ flex: 1, height: `${(v/max)*100}%`, background: i === maxIdx ? C.blue : C.blueSoft, borderRadius: "8px 8px 3px 3px", minHeight: 6 }} />)}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>{labels.map((l, i) => <div key={i} style={{ flex: 1, textAlign: "center", color: C.sub, fontSize: 12, fontWeight: 600 }}>{l}</div>)}</div>
    </div>
  );
}
function HBarChart({ rows }) {
  const max = Math.max(...rows.map(r => r[1]));
  const cols = [C.blue, C.green, C.amber, C.violet, C.rose, C.sub];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {rows.map(([label, v], i) => (
        <div key={label}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}><span style={{ fontWeight: 700, fontSize: 14 }}>{label}</span><span style={{ fontWeight: 800, fontSize: 14, color: C.sub }}>{v}</span></div>
          <div style={{ height: 12, background: C.cardAlt, borderRadius: 999 }}><div style={{ width: `${(v/max)*100}%`, height: 12, background: cols[i % cols.length], borderRadius: 999 }} /></div>
        </div>
      ))}
    </div>
  );
}
function DonutChart({ segments, labels }) {
  let acc = 0; const R = 54, cx = 70, cy = 70, circ = 2 * Math.PI * R;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap", justifyContent: "center" }}>
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={C.cardAlt} strokeWidth="20" />
        {segments.map(([pct, col], i) => {
          const len = (pct/100)*circ; const off = (acc/100)*circ; acc += pct;
          return <circle key={i} cx={cx} cy={cy} r={R} fill="none" stroke={col} strokeWidth="20" strokeDasharray={`${len} ${circ-len}`} strokeDashoffset={-off} transform={`rotate(-90 ${cx} ${cy})`} />;
        })}
        <text x="70" y="66" textAnchor="middle" fontSize="26" fontWeight="800" fill={C.ink}>{segments[0][0]}%</text>
        <text x="70" y="86" textAnchor="middle" fontSize="11" fill={C.sub}>{labels[0]}</text>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {segments.map(([pct, col], i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 10 }}><span style={{ width: 12, height: 12, borderRadius: 4, background: col }} /><span style={{ fontWeight: 700, fontSize: 14 }}>{labels[i]}</span><span style={{ color: C.sub, fontWeight: 700, fontSize: 14 }}>{pct}%</span></div>
        ))}
      </div>
    </div>
  );
}
function StatsFor({ report, t, rtl, money }) {
  const sets = {
    volume: [[t.totalCalls, rtl ? "١٬٥٤٠" : "1,540"], [t.avgCalls, rtl ? "٤٩٫٧" : "49.7"]],
    duration: [[rtl ? "متوسط المدة" : "Avg duration", rtl ? "١:١٢" : "1:12"], [rtl ? "الأطول" : "Longest", rtl ? "٤:٣٠" : "4:30"]],
    sentiment: [[rtl ? "إيجابي" : "Positive", "62%"], [rtl ? "قلق" : "Concerned", "12%"]],
    peak: [[rtl ? "ساعة الذروة" : "Peak hour", rtl ? "٣ م" : "3 PM"], [rtl ? "الأهدأ" : "Quietest", rtl ? "٩ م" : "9 PM"]],
    afterhours: [[rtl ? "بعد العمل" : "After-hours", rtl ? "١١٨" : "118"], [rtl ? "نسبة الالتقاط" : "Capture rate", "94%"]],
    bookvol: [[t.bookings, rtl ? "٢٤٣" : "243"], [rtl ? "معدل التحويل" : "Conversion", "38%"]],
    revenue: [[rtl ? "الإيراد" : "Revenue", money(184500)], [rtl ? "متوسط الحجز" : "Avg booking", money(760)]],
    bytreatment: [[rtl ? "الأكثر حجزاً" : "Top", "HydraFacial"], [rtl ? "الأعلى إيراداً" : "Top revenue", "Filler"]],
    channel: [[rtl ? "صوت" : "Voice", "62%"], [rtl ? "واتساب" : "WhatsApp", "26%"]],
  };
  const s = sets[report.id] || sets.volume;
  return (
    <div style={{ display: "flex", gap: 14 }}>
      {s.map(([label, val], i) => (
        <Card key={i} style={{ padding: 20, flex: 1 }}>
          <div style={{ color: C.sub, fontWeight: 700, fontSize: 14, marginBottom: 8 }}>{label}</div>
          <div style={{ fontSize: 26, fontWeight: 900, letterSpacing: -0.5 }}>{val}</div>
        </Card>
      ))}
    </div>
  );
}

function Appts({ t, rtl, lang }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Header title={t.apptsTitle} sub={t.apptsSub} />
      <Card style={{ padding: 16, background: C.cardAlt, border: `1.5px dashed ${C.line}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, color: C.sub }}><Calendar size={20} /><span style={{ fontWeight: 600, lineHeight: 1.4 }}>{t.calDim}</span></div>
      </Card>
      <div style={{ color: C.sub, fontWeight: 800, fontSize: 15, padding: "4px 6px" }}>{t.upcoming}</div>
      {APPTS.map((a, i) => (
        <Card key={i} style={{ padding: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ width: 58, height: 62, borderRadius: 16, background: C.blueSoft, display: "grid", placeItems: "center", flexShrink: 0 }}>
              <div style={{ color: C.blueDeep, fontWeight: 800, fontSize: 12 }}>{a.day[lang]}</div>
              <div style={{ color: C.blueDeep, fontWeight: 900, fontSize: 22, lineHeight: 1 }}>{a.date}</div>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 800, fontSize: 17 }}>{a.name}</div>
              <div style={{ color: C.ink, fontSize: 15, margin: "2px 0" }}>{lang === "ar" ? a.svc.ar : a.svc.en}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
                <Pill bg={C.cardAlt} fg={C.sub} style={{ fontSize: 12 }}><Clock size={12} /> {a.time}</Pill>
                <Pill bg={C.greenSoft} fg={C.green} style={{ fontSize: 12 }}><Sparkles size={12} /> {a.via}</Pill>
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

function SettingsPage({ t, rtl, tab, setTab, openFaq, setOpenFaq, lang, branch }) {
  const tabs = [["general", SettingsIcon], ["voice", Mic], ["booking", CalendarCheck], ["faq", MessageSquare]];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", gap: 24, borderBottom: `1px solid ${C.line}`, overflowX: "auto" }}>
        {tabs.map(([k, Ic]) => {
          const on = tab === k;
          return <button key={k} onClick={() => setTab(k)} style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "12px 2px", background: "transparent", border: "none", borderBottom: on ? `3px solid ${C.blue}` : "3px solid transparent", color: on ? C.blue : C.sub, fontWeight: 800, fontSize: 16, cursor: "pointer", whiteSpace: "nowrap", fontFamily: "inherit" }}><Ic size={19} /> {t.tabs[k]}</button>;
        })}
      </div>

      {tab === "general" && (<>
        <div style={{ fontWeight: 900, fontSize: 21 }}>{t.locationInfo}</div>
        <Card style={{ padding: 22 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}><MapPin size={19} color={C.sub} /><span style={{ fontWeight: 600 }}>{branch.addr[lang]}</span></div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}><Phone size={19} color={C.sub} /><span style={{ fontWeight: 600, direction: "ltr" }}>+966 11 234 5678</span></div>
          <button style={{ ...btnGhost, margin: "0 auto", display: "flex" }}><PhoneCall size={17} /> {t.testCall}</button>
        </Card>
        <div style={{ fontWeight: 900, fontSize: 21 }}>{t.hours}</div>
        <Card style={{ padding: 22 }}>
          <p style={{ margin: "0 0 16px", color: C.sub }}>{t.hoursSub}</p>
          {(rtl ? ["السبت","الأحد","الإثنين","الثلاثاء","الأربعاء","الخميس"] : ["Saturday","Sunday","Monday","Tuesday","Wednesday","Thursday"]).map((d, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 0", borderTop: i ? `1px solid ${C.line}` : "none" }}>
              <Toggle on /><span style={{ fontWeight: 800, minWidth: 90 }}>{d}</span><Pill bg={C.cardAlt} fg={C.ink} style={{ [rtl ? "marginRight" : "marginLeft"]: "auto" }}>1:00 PM → 9:00 PM</Pill>
            </div>
          ))}
          <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 0", borderTop: `1px solid ${C.line}`, opacity: .5 }}>
            <Toggle on={false} /><span style={{ fontWeight: 800 }}>{rtl ? "الجمعة" : "Friday"}</span><span style={{ [rtl ? "marginRight" : "marginLeft"]: "auto", color: C.sub, fontWeight: 700 }}>{rtl ? "مغلق" : "Closed"}</span>
          </div>
        </Card>
        <div style={{ fontWeight: 900, fontSize: 21 }}>{t.greetingMsgs}</div>
        <Card style={{ padding: 22 }}>
          <div style={{ fontWeight: 800, fontSize: 17, marginBottom: 4 }}>{t.openGreeting} <span style={{ color: C.rose }}>*</span></div>
          <p style={{ margin: "0 0 12px", color: C.sub }}>{t.openGreetingSub}</p>
          <div style={{ background: C.cardAlt, borderRadius: 16, padding: 16, lineHeight: 1.6, fontWeight: 500 }}>{rtl ? "أهلاً بك في عيادة ديفينيا. كيف يمكنني مساعدتك اليوم؟" : "Hello, welcome to Divinia Clinic. How may I help you today?"}</div>
          <div style={{ borderTop: `1px solid ${C.line}`, margin: "20px 0 16px" }} />
          <div style={{ fontWeight: 800, fontSize: 17, marginBottom: 4 }}>{t.closedGreeting} <span style={{ color: C.rose }}>*</span></div>
          <p style={{ margin: "0 0 12px", color: C.sub, lineHeight: 1.5 }}>{t.closedGreetingSub}</p>
          <div style={{ background: C.cardAlt, borderRadius: 16, padding: 16, lineHeight: 1.6, fontWeight: 500 }}>{rtl ? "شكراً لاتصالك بعيادة ديفينيا. نحن مغلقون حالياً، لكن يمكنني تحديد موعد لك ونعاود الاتصال بك في ساعات العمل." : "Thanks for calling Divinia Clinic. We're currently closed, but I can schedule an appointment for you and we'll follow up during clinic hours."}</div>
        </Card>

        <div style={{ fontWeight: 900, fontSize: 21 }}>{t.holidayHours}</div>
        <HolidaySection t={t} rtl={rtl} lang={lang} />

        <div style={{ fontWeight: 900, fontSize: 21 }}>{t.tempClosure}</div>
        <Card style={{ padding: 22 }}>
          <p style={{ margin: "0 0 16px", color: C.sub, lineHeight: 1.55 }}>{t.tempClosureSub}</p>
          <button style={{ width: "100%", background: C.amberSoft, border: `1.5px solid ${C.amber}`, borderRadius: 14, padding: 15, fontWeight: 800, fontSize: 15, color: C.amber, cursor: "pointer", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, fontFamily: "inherit" }}>
            <Pause size={18} /> {t.setTempClosure}
          </button>
        </Card>
      </>)}

      {tab === "voice" && (<>
        <Card style={{ padding: 22 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}><Mic size={20} color={C.blue} /><h3 style={{ margin: 0, fontSize: 19, fontWeight: 900 }}>{t.selectVoice}</h3></div>
          <p style={{ margin: "0 0 16px", color: C.sub }}>{t.selectVoiceSub}</p>
          <VoiceRow name={rtl ? "ريم" : "Reem"} desc={t.khaleeji} active /><div style={{ height: 10 }} /><VoiceRow name="Marissa" desc={t.american} active={false} />
        </Card>
        <Card style={{ padding: 22 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}><SettingsIcon size={19} color={C.blue} /><h3 style={{ margin: 0, fontSize: 18, fontWeight: 900 }}>{t.voiceSpeed}</h3></div>
          <p style={{ margin: "0 0 18px", color: C.sub }}>{t.voiceSpeedSub}</p>
          <Slider pct={62} /><div style={{ display: "flex", justifyContent: "space-between", color: C.sub, fontSize: 13, fontWeight: 600, marginTop: 8 }}><span>{t.slowest}</span><span>{t.normal}</span><span>{t.fastest}</span></div>
        </Card>
        <Card style={{ padding: 22 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 6 }}>
            <div><h3 style={{ margin: "0 0 4px", fontSize: 18, fontWeight: 900 }}>{t.ambient}</h3><p style={{ margin: 0, color: C.sub, maxWidth: 280, lineHeight: 1.45 }}>{t.ambientSub}</p></div><Toggle on />
          </div>
          <div style={{ height: 12 }} /><Slider pct={34} /><div style={{ display: "flex", justifyContent: "space-between", color: C.sub, fontSize: 13, fontWeight: 600, marginTop: 8 }}><span>{t.quiet}</span><span>{t.normal}</span><span>{t.loud}</span></div>
        </Card>
      </>)}

      {tab === "booking" && (<>
        <Header title={t.bookingTitle} sub={t.bookingSub} noTop />
        <Card style={{ padding: 22 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <IconBox bg={C.greenSoft} fg={C.green}><CalendarCheck size={22} /></IconBox>
              <div><div style={{ fontWeight: 900, fontSize: 17 }}>{t.calcom}</div><Pill bg={C.greenSoft} fg={C.green} style={{ fontSize: 11, marginTop: 4 }}><CheckCircle2 size={12} /> {t.connected}</Pill></div>
            </div>
            <button style={{ background: "transparent", border: "none", color: C.blue, fontWeight: 800, cursor: "pointer", display: "inline-flex", gap: 5, alignItems: "center" }}>{t.manage} <ArrowUpRight size={16} /></button>
          </div>
          <p style={{ margin: "10px 0 0", color: C.sub, lineHeight: 1.5 }}>{t.calcomBody}</p>
        </Card>
        <Card style={{ padding: 22 }}>
          <ToggleRow title={t.smsConfirm} sub={t.smsConfirmSub} on /><div style={{ borderTop: `1px solid ${C.line}`, margin: "16px 0" }} /><ToggleRow title={t.smsRemind} sub={t.smsRemindSub} on />
        </Card>
      </>)}

      {tab === "faq" && (<>
        <Card style={{ padding: 22 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
            <div style={{ display: "flex", gap: 12 }}><HelpCircle size={22} color={C.blue} style={{ marginTop: 2 }} /><div><h3 style={{ margin: "0 0 6px", fontSize: 19, fontWeight: 900 }}>{t.faqTitle}</h3><p style={{ margin: 0, color: C.sub, maxWidth: 280, lineHeight: 1.45 }}>{t.faqSub}</p></div></div>
            <Pill bg={C.cardAlt} fg={C.ink} style={{ fontSize: 12 }}>{t.expandAll} <ChevronDown size={14} /></Pill>
          </div>
        </Card>
        {FAQS.map((f, i) => (
          <Card key={i} style={{ padding: "18px 20px" }}>
            <div onClick={() => setOpenFaq(openFaq === i ? -1 : i)} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", gap: 12 }}>
              <span style={{ fontWeight: 800, fontSize: 16 }}>{lang === "ar" ? f.ar : f.en}</span>
              <ChevronDown size={20} color={C.sub} style={{ transform: openFaq === i ? "rotate(180deg)" : "none", transition: ".2s", flexShrink: 0 }} />
            </div>
            {openFaq === i && <p style={{ margin: "12px 0 0", color: C.sub, lineHeight: 1.6, fontSize: 15 }}>{lang === "ar" ? f.a_ar : f.a_en}</p>}
          </Card>
        ))}
      </>)}
    </div>
  );
}

function HolidaySection({ t, rtl, lang }) {
  const [items, setItems] = useState(HOLIDAYS);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [closed, setClosed] = useState(true);
  const [hours, setHours] = useState("4:00 PM → 9:00 PM");

  const add = () => {
    const nm = name.trim() || (rtl ? "عطلة جديدة" : "New holiday");
    const dt = date.trim() || (rtl ? "قريباً" : "TBD");
    setItems([{ name: { en: nm, ar: nm }, date: { en: dt, ar: dt }, closed, hours: closed ? "" : hours, upcoming: true }, ...items]);
    setAdding(false); setName(""); setDate(""); setClosed(true);
  };
  const remove = (idx) => setItems(items.filter((_, i) => i !== idx));

  const input = { width: "100%", boxSizing: "border-box", padding: "13px 14px", borderRadius: 12, border: `1.5px solid ${C.line}`, background: C.card, fontSize: 15, color: C.ink, outline: "none", fontFamily: "inherit" };

  return (
    <Card style={{ padding: 22 }}>
      <p style={{ margin: "0 0 16px", color: C.sub, lineHeight: 1.55 }}>{t.holidayHoursSub}</p>

      {items.map((h, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 0", borderTop: i ? `1px solid ${C.line}` : "none" }}>
          <IconBox bg={h.upcoming ? C.blueSoft : C.cardAlt} fg={h.upcoming ? C.blue : C.sub}><Calendar size={20} /></IconBox>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 800, fontSize: 16 }}>{h.name[lang]}</div>
            <div style={{ color: C.sub, fontSize: 13.5, marginTop: 2, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span>{h.date[lang]}</span>
              {h.closed
                ? <Pill bg={C.roseSoft} fg={C.rose} style={{ fontSize: 11 }}>{t.closedAllDay}</Pill>
                : <Pill bg={C.greenSoft} fg={C.green} style={{ fontSize: 11 }}>{h.hours}</Pill>}
              <Pill bg={C.cardAlt} fg={C.sub} style={{ fontSize: 11 }}>{h.upcoming ? t.upcomingLabel : t.passedLabel}</Pill>
            </div>
          </div>
          <button onClick={() => remove(i)} style={{ background: "transparent", border: "none", cursor: "pointer", color: C.rose, fontWeight: 700, fontSize: 13, flexShrink: 0, fontFamily: "inherit" }}>{t.remove}</button>
        </div>
      ))}

      {adding ? (
        <div style={{ marginTop: 16, background: C.cardAlt, borderRadius: 16, padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label style={{ fontWeight: 700, fontSize: 13.5, color: C.sub, display: "block", marginBottom: 6 }}>{t.holidayName}</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder={rtl ? "مثال: عيد الأضحى" : "e.g. Eid al-Adha"} style={input} />
          </div>
          <div>
            <label style={{ fontWeight: 700, fontSize: 13.5, color: C.sub, display: "block", marginBottom: 6 }}>{t.date}</label>
            <input value={date} onChange={e => setDate(e.target.value)} placeholder={rtl ? "مثال: ٢٧ يونيو ٢٠٢٦" : "e.g. Jun 27, 2026"} style={input} />
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <span style={{ fontWeight: 800, fontSize: 15 }}>{t.closedAllDay}</span>
            <div onClick={() => setClosed(c => !c)} style={{ cursor: "pointer" }}><Toggle on={closed} /></div>
          </div>
          {!closed && (
            <div>
              <label style={{ fontWeight: 700, fontSize: 13.5, color: C.sub, display: "block", marginBottom: 6 }}>{t.specialHours}</label>
              <input value={hours} onChange={e => setHours(e.target.value)} style={input} />
            </div>
          )}
          <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
            <button onClick={() => setAdding(false)} style={{ flex: 1, background: C.card, border: `1.5px solid ${C.line}`, borderRadius: 999, padding: "12px", fontWeight: 800, cursor: "pointer", color: C.ink, fontFamily: "inherit" }}>{t.cancel}</button>
            <button onClick={add} style={{ flex: 1, background: C.blue, border: "none", borderRadius: 999, padding: "12px", fontWeight: 800, cursor: "pointer", color: "#fff", fontFamily: "inherit" }}>{t.save}</button>
          </div>
        </div>
      ) : (
        <button onClick={() => setAdding(true)} style={{ width: "100%", marginTop: 16, background: C.cardAlt, border: `1.5px dashed ${C.line}`, borderRadius: 14, padding: 15, fontWeight: 800, fontSize: 15, color: C.ink, cursor: "pointer", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, fontFamily: "inherit" }}>
          <Plus size={18} color={C.blue} /> {t.addHoliday}
        </button>
      )}
    </Card>
  );
}

function Support({ t }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, paddingTop: 8 }}>
      <h1 style={{ fontSize: 28, fontWeight: 900, margin: 0 }}>{navLabel(t, "support")}</h1>
      <Card style={{ padding: 26, textAlign: "center" }}>
        <IconBox bg={C.blueSoft} fg={C.blue}><MessageSquare size={22} /></IconBox>
        <div style={{ height: 12 }} />
        <div style={{ fontWeight: 900, fontSize: 20, marginBottom: 6 }}>AtlasPrimeX Support</div>
        <p style={{ color: C.sub, margin: "0 0 16px" }}>support@atlasprimex.com</p>
        <button style={{ ...btnDark, margin: "0 auto" }}><MessageSquare size={16} /> Start chat</button>
      </Card>
    </div>
  );
}

function Header({ title, sub, noTop }) {
  return (
    <div style={{ padding: noTop ? "4px 4px" : "8px 4px 0" }}>
      <h1 style={{ fontSize: 28, fontWeight: 900, margin: "0 0 6px", letterSpacing: -0.5 }}>{title}</h1>
      <p style={{ margin: 0, color: C.sub, lineHeight: 1.45 }}>{sub}</p>
    </div>
  );
}
function Toggle({ on }) {
  return <div style={{ width: 48, height: 28, borderRadius: 999, background: on ? C.blue : "#D8D2C6", position: "relative", flexShrink: 0, transition: ".2s" }}><div style={{ position: "absolute", top: 3, left: on ? 23 : 3, width: 22, height: 22, borderRadius: 999, background: "#fff", transition: ".2s", boxShadow: "0 1px 3px rgba(0,0,0,.2)" }} /></div>;
}
function ToggleRow({ title, sub, on }) {
  return <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}><div><div style={{ fontWeight: 800, fontSize: 16, marginBottom: 4 }}>{title}</div><div style={{ color: C.sub, lineHeight: 1.45 }}>{sub}</div></div><Toggle on={on} /></div>;
}
function Slider({ pct }) {
  return <div style={{ position: "relative", height: 6, background: C.line, borderRadius: 999 }}><div style={{ position: "absolute", left: 0, top: 0, height: 6, width: `${pct}%`, background: C.ink, borderRadius: 999 }} /><div style={{ position: "absolute", top: -7, left: `calc(${pct}% - 10px)`, width: 20, height: 20, borderRadius: 999, background: C.ink, border: "3px solid #fff", boxShadow: "0 1px 4px rgba(0,0,0,.25)" }} /></div>;
}
function VoiceRow({ name, desc, active }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, background: active ? C.blueSoft : C.cardAlt, borderRadius: 16, padding: 14, border: active ? `1.5px solid ${C.blue}` : "1.5px solid transparent" }}>
      <div style={{ width: 44, height: 44, borderRadius: 999, background: `linear-gradient(135deg,${C.blue},${C.blueDeep})`, display: "grid", placeItems: "center", color: "#fff", fontWeight: 800 }}>{name[0]}</div>
      <div style={{ flex: 1 }}><div style={{ fontWeight: 800, fontSize: 16 }}>{name}</div><div style={{ color: C.sub, fontSize: 13.5 }}>{desc}</div></div>
      <div style={{ width: 40, height: 40, borderRadius: 999, border: `2px solid ${active ? C.blue : C.sub}`, display: "grid", placeItems: "center", cursor: "pointer" }}><Play size={16} color={active ? C.blue : C.sub} /></div>
    </div>
  );
}

const btnDark = { background: C.ink, color: "#fff", border: "none", borderRadius: 999, padding: "12px 20px", fontWeight: 800, fontSize: 15, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 8, fontFamily: "inherit" };
const btnGhost = { background: C.card, border: `1.5px solid ${C.line}`, borderRadius: 999, padding: "11px 22px", fontWeight: 800, fontSize: 15, color: C.ink, cursor: "pointer", alignItems: "center", gap: 8, fontFamily: "inherit" };
const backBtn = { background: "transparent", border: "none", color: C.sub, fontWeight: 800, fontSize: 15, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 0", alignSelf: "flex-start", fontFamily: "inherit" };

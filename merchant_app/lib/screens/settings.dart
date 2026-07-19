import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/merchant_repository.dart';
import '../data/models.dart';
import '../l10n/strings.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(languageProvider);
    final s = S.of(lang);
    final rtl = lang == 'ar';
    final tab = ref.watch(settingsTabProvider);
    final branch = ref.watch(branchProvider);

    const tabs = [
      ['general', Icons.settings_outlined],
      ['voice', Icons.mic_none],
      ['booking', Icons.event_available],
      ['faq', Icons.chat_bubble_outline],
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // tab bar
        Container(
          decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AppColors.line))),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (final t in tabs)
                  Padding(
                    padding: const EdgeInsets.only(right: 24),
                    child: InkWell(
                      onTap: () => ref.read(settingsTabProvider.notifier).state = t[0] as String,
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        decoration: BoxDecoration(
                          border: Border(
                            bottom: BorderSide(color: tab == t[0] ? AppColors.blue : Colors.transparent, width: 3),
                          ),
                        ),
                        child: Row(mainAxisSize: MainAxisSize.min, children: [
                          Icon(t[1] as IconData, size: 19, color: tab == t[0] ? AppColors.blue : AppColors.sub),
                          const SizedBox(width: 8),
                          Text(s.v('tab_${t[0]}'),
                              style: TextStyle(
                                  color: tab == t[0] ? AppColors.blue : AppColors.sub,
                                  fontWeight: FontWeight.w800,
                                  fontSize: 16)),
                        ]),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        if (tab == 'general') _General(s: s, rtl: rtl, lang: lang, branch: branch),
        if (tab == 'voice') _Voice(s: s, rtl: rtl),
        if (tab == 'booking') _Booking(s: s),
        if (tab == 'faq') _Faq(s: s, lang: lang, ref: ref),
      ],
    );
  }
}

// ---------- GENERAL ----------
class _General extends StatelessWidget {
  final S s;
  final bool rtl;
  final String lang;
  final Branch branch;
  const _General({required this.s, required this.rtl, required this.lang, required this.branch});

  @override
  Widget build(BuildContext context) {
    final days = rtl
        ? ['السبت', 'الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
        : ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday'];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionTitle(s.v('locationInfo')),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            children: [
              Row(children: [
                const Icon(Icons.location_on_outlined, size: 19, color: AppColors.sub),
                const SizedBox(width: 10),
                Expanded(child: Text(loc(branch.addr, lang), style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.ink))),
              ]),
              const SizedBox(height: 12),
              Row(children: const [
                Icon(Icons.call_outlined, size: 19, color: AppColors.sub),
                SizedBox(width: 10),
                Text('+966 11 234 5678', textDirection: TextDirection.ltr, style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.ink)),
              ]),
              const SizedBox(height: 18),
              PillButton.ghost(s.v('testCall'), icon: Icons.phone_in_talk_outlined),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionTitle(s.v('hours')),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(s.v('hoursSub'), style: const TextStyle(color: AppColors.sub)),
              const SizedBox(height: 16),
              for (int i = 0; i < days.length; i++)
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  decoration: BoxDecoration(border: i == 0 ? null : const Border(top: BorderSide(color: AppColors.line))),
                  child: Row(children: [
                    const AppToggle(on: true),
                    const SizedBox(width: 14),
                    SizedBox(width: 90, child: Text(days[i], style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink))),
                    const Spacer(),
                    Pill(bg: AppColors.cardAlt, fg: AppColors.ink, child: hoursRow('1:00 PM → 9:00 PM')),
                  ]),
                ),
              Opacity(
                opacity: 0.5,
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  decoration: const BoxDecoration(border: Border(top: BorderSide(color: AppColors.line))),
                  child: Row(children: [
                    const AppToggle(on: false),
                    const SizedBox(width: 14),
                    Text(s.v('friday'), style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink)),
                    const Spacer(),
                    Text(s.v('closed'), style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w700)),
                  ]),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionTitle(s.v('greetingMsgs')),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _greetingTitle(s.v('openGreeting')),
              const SizedBox(height: 4),
              Text(s.v('openGreetingSub'), style: const TextStyle(color: AppColors.sub)),
              const SizedBox(height: 12),
              _greetingBox(rtl
                  ? 'أهلاً بك في عيادة ديفينيا. كيف يمكنني مساعدتك اليوم؟'
                  : 'Hello, welcome to Divinia Clinic. How may I help you today?'),
              const Padding(padding: EdgeInsets.symmetric(vertical: 20), child: Divider(color: AppColors.line, height: 1)),
              _greetingTitle(s.v('closedGreeting')),
              const SizedBox(height: 4),
              Text(s.v('closedGreetingSub'), style: const TextStyle(color: AppColors.sub, height: 1.5)),
              const SizedBox(height: 12),
              _greetingBox(rtl
                  ? 'شكراً لاتصالك بعيادة ديفينيا. نحن مغلقون حالياً، لكن يمكنني تحديد موعد لك ونعاود الاتصال بك في ساعات العمل.'
                  : "Thanks for calling Divinia Clinic. We're currently closed, but I can schedule an appointment for you and we'll follow up during clinic hours."),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionTitle(s.v('holidayHours')),
        const SizedBox(height: 16),
        _HolidaySection(s: s, rtl: rtl, lang: lang),
        const SizedBox(height: 16),
        SectionTitle(s.v('tempClosure')),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(s.v('tempClosureSub'), style: const TextStyle(color: AppColors.sub, height: 1.55)),
              const SizedBox(height: 16),
              InkWell(
                onTap: () {},
                borderRadius: BorderRadius.circular(14),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(15),
                  decoration: BoxDecoration(
                    color: AppColors.amberSoft,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppColors.amber, width: 1.5),
                  ),
                  child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                    const Icon(Icons.pause, size: 18, color: AppColors.amber),
                    const SizedBox(width: 8),
                    Text(s.v('setTempClosure'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.amber)),
                  ]),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _greetingTitle(String text) => Text.rich(TextSpan(
        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17, color: AppColors.ink),
        children: [TextSpan(text: text), const TextSpan(text: ' *', style: TextStyle(color: AppColors.rose))],
      ));

  Widget _greetingBox(String text) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(16)),
        child: Text(text, style: const TextStyle(height: 1.6, fontWeight: FontWeight.w500, color: AppColors.ink)),
      );
}

// ---------- HOLIDAY MANAGER ----------
class _HolidaySection extends ConsumerStatefulWidget {
  final S s;
  final bool rtl;
  final String lang;
  const _HolidaySection({required this.s, required this.rtl, required this.lang});
  @override
  ConsumerState<_HolidaySection> createState() => _HolidaySectionState();
}

class _HolidaySectionState extends ConsumerState<_HolidaySection> {
  late List<Holiday> items = [...ref.read(merchantRepositoryProvider).holidays()];
  bool adding = false;
  final nameCtl = TextEditingController();
  final dateCtl = TextEditingController();
  final hoursCtl = TextEditingController(text: '4:00 PM → 9:00 PM');
  bool closed = true;

  @override
  void dispose() {
    nameCtl.dispose();
    dateCtl.dispose();
    hoursCtl.dispose();
    super.dispose();
  }

  void _add() {
    final s = widget.s;
    final nm = nameCtl.text.trim().isEmpty ? s.v('newHoliday') : nameCtl.text.trim();
    final dt = dateCtl.text.trim().isEmpty ? s.v('tbd') : dateCtl.text.trim();
    setState(() {
      items = [
        Holiday(name: {'en': nm, 'ar': nm}, date: {'en': dt, 'ar': dt}, closed: closed, hours: closed ? '' : hoursCtl.text, upcoming: true),
        ...items,
      ];
      adding = false;
      nameCtl.clear();
      dateCtl.clear();
      closed = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.s;
    final lang = widget.lang;
    return AppCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(s.v('holidayHoursSub'), style: const TextStyle(color: AppColors.sub, height: 1.55)),
          for (int i = 0; i < items.length; i++)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(border: i == 0 ? null : const Border(top: BorderSide(color: AppColors.line))),
              child: Row(
                children: [
                  IconBox(
                    icon: Icons.calendar_today_outlined,
                    bg: items[i].upcoming ? AppColors.blueSoft : AppColors.cardAlt,
                    fg: items[i].upcoming ? AppColors.blue : AppColors.sub,
                    iconSize: 20,
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(loc(items[i].name, lang), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: AppColors.ink)),
                        const SizedBox(height: 2),
                        Wrap(spacing: 8, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
                          Text(loc(items[i].date, lang), style: const TextStyle(color: AppColors.sub, fontSize: 13.5)),
                          if (items[i].closed)
                            Pill(bg: AppColors.roseSoft, fg: AppColors.rose, fontSize: 11, child: Text(s.v('closedAllDay')))
                          else
                            Pill(bg: AppColors.greenSoft, fg: AppColors.green, fontSize: 11, child: hoursRow(items[i].hours, size: 11)),
                          Pill(bg: AppColors.cardAlt, fg: AppColors.sub, fontSize: 11, child: Text(items[i].upcoming ? s.v('upcomingLabel') : s.v('passedLabel'))),
                        ]),
                      ],
                    ),
                  ),
                  InkWell(
                    onTap: () => setState(() => items = [for (int j = 0; j < items.length; j++) if (j != i) items[j]]),
                    child: Text(s.v('remove'), style: const TextStyle(color: AppColors.rose, fontWeight: FontWeight.w700, fontSize: 13)),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 16),
          if (adding)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(16)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _fieldLabel(s.v('holidayName')),
                  _input(nameCtl, s.v('newHolidayHint')),
                  const SizedBox(height: 12),
                  _fieldLabel(s.v('date')),
                  _input(dateCtl, s.v('dateHint')),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(s.v('closedAllDay'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.ink)),
                      AppToggle(on: closed, onChanged: (v) => setState(() => closed = v)),
                    ],
                  ),
                  if (!closed) ...[
                    const SizedBox(height: 12),
                    _fieldLabel(s.v('specialHours')),
                    _input(hoursCtl, ''),
                  ],
                  const SizedBox(height: 16),
                  Row(children: [
                    Expanded(child: PillButton.ghost(s.v('cancel'), fullWidth: true, onTap: () => setState(() => adding = false))),
                    const SizedBox(width: 10),
                    Expanded(child: PillButton.primary(s.v('save'), fullWidth: true, onTap: _add)),
                  ]),
                ],
              ),
            )
          else
            InkWell(
              onTap: () => setState(() => adding = true),
              borderRadius: BorderRadius.circular(14),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(15),
                decoration: BoxDecoration(
                  color: AppColors.cardAlt,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.line, width: 1.5),
                ),
                child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  const Icon(Icons.add, size: 18, color: AppColors.blue),
                  const SizedBox(width: 8),
                  Text(s.v('addHoliday'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.ink)),
                ]),
              ),
            ),
        ],
      ),
    );
  }

  Widget _fieldLabel(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5, color: AppColors.sub)),
      );

  Widget _input(TextEditingController ctl, String hint) => TextField(
        controller: ctl,
        style: const TextStyle(fontSize: 15, color: AppColors.ink),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: const TextStyle(color: AppColors.sub),
          filled: true,
          fillColor: AppColors.card,
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.line, width: 1.5)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.blue, width: 1.5)),
        ),
      );
}

// ---------- VOICE ----------
class _Voice extends StatelessWidget {
  final S s;
  final bool rtl;
  const _Voice({required this.s, required this.rtl});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                const Icon(Icons.mic_none, size: 20, color: AppColors.blue),
                const SizedBox(width: 10),
                Text(s.v('selectVoice'), style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900, color: AppColors.ink)),
              ]),
              const SizedBox(height: 6),
              Text(s.v('selectVoiceSub'), style: const TextStyle(color: AppColors.sub)),
              const SizedBox(height: 16),
              VoiceRow(name: rtl ? 'ريم' : 'Reem', desc: s.v('khaleeji'), active: true),
              const SizedBox(height: 10),
              VoiceRow(name: 'Marissa', desc: s.v('american'), active: false),
            ],
          ),
        ),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                const Icon(Icons.settings_outlined, size: 19, color: AppColors.blue),
                const SizedBox(width: 10),
                Text(s.v('voiceSpeed'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.ink)),
              ]),
              const SizedBox(height: 6),
              Text(s.v('voiceSpeedSub'), style: const TextStyle(color: AppColors.sub)),
              const SizedBox(height: 18),
              const StaticSlider(pct: 62),
              const SizedBox(height: 8),
              _sliderLabels(s.v('slowest'), s.v('normal'), s.v('fastest')),
            ],
          ),
        ),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(s.v('ambient'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.ink)),
                        const SizedBox(height: 4),
                        Text(s.v('ambientSub'), style: const TextStyle(color: AppColors.sub, height: 1.45)),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  const AppToggle(on: true),
                ],
              ),
              const SizedBox(height: 12),
              const StaticSlider(pct: 34),
              const SizedBox(height: 8),
              _sliderLabels(s.v('quiet'), s.v('normal'), s.v('loud')),
            ],
          ),
        ),
      ],
    );
  }

  Widget _sliderLabels(String a, String b, String c) => Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(a, style: const TextStyle(color: AppColors.sub, fontSize: 13, fontWeight: FontWeight.w600)),
          Text(b, style: const TextStyle(color: AppColors.sub, fontSize: 13, fontWeight: FontWeight.w600)),
          Text(c, style: const TextStyle(color: AppColors.sub, fontSize: 13, fontWeight: FontWeight.w600)),
        ],
      );
}

// ---------- BOOKING ----------
class _Booking extends StatelessWidget {
  final S s;
  const _Booking({required this.s});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ScreenHeader(title: s.v('bookingTitle'), sub: s.v('bookingSub'), noTop: true),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        const IconBox(icon: Icons.event_available, bg: AppColors.greenSoft, fg: AppColors.green),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(s.v('calcom'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: AppColors.ink)),
                              const SizedBox(height: 4),
                              Pill(
                                bg: AppColors.greenSoft,
                                fg: AppColors.green,
                                fontSize: 11,
                                child: Row(mainAxisSize: MainAxisSize.min, children: [
                                  const Icon(Icons.check_circle, size: 12, color: AppColors.green),
                                  const SizedBox(width: 5),
                                  Text(s.v('connected')),
                                ]),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  Row(mainAxisSize: MainAxisSize.min, children: [
                    Text(s.v('manage'), style: const TextStyle(color: AppColors.blue, fontWeight: FontWeight.w800)),
                    const SizedBox(width: 5),
                    const Icon(Icons.north_east, size: 16, color: AppColors.blue),
                  ]),
                ],
              ),
              const SizedBox(height: 10),
              Text(s.v('calcomBody'), style: const TextStyle(color: AppColors.sub, height: 1.5)),
            ],
          ),
        ),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            children: [
              _toggleRow(s.v('smsConfirm'), s.v('smsConfirmSub')),
              const Padding(padding: EdgeInsets.symmetric(vertical: 16), child: Divider(color: AppColors.line, height: 1)),
              _toggleRow(s.v('smsRemind'), s.v('smsRemindSub')),
            ],
          ),
        ),
      ],
    );
  }

  Widget _toggleRow(String title, String sub) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: AppColors.ink)),
                const SizedBox(height: 4),
                Text(sub, style: const TextStyle(color: AppColors.sub, height: 1.45)),
              ],
            ),
          ),
          const SizedBox(width: 12),
          const AppToggle(on: true),
        ],
      );
}

// ---------- FAQ ----------
class _Faq extends StatelessWidget {
  final S s;
  final String lang;
  final WidgetRef ref;
  const _Faq({required this.s, required this.lang, required this.ref});

  @override
  Widget build(BuildContext context) {
    final faqs = ref.read(merchantRepositoryProvider).faqs();
    final open = ref.watch(openFaqProvider);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(padding: EdgeInsets.only(top: 2), child: Icon(Icons.help_outline, size: 22, color: AppColors.blue)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(s.v('faqTitle'), style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900, color: AppColors.ink)),
                    const SizedBox(height: 6),
                    Text(s.v('faqSub'), style: const TextStyle(color: AppColors.sub, height: 1.45)),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Pill(bg: AppColors.cardAlt, fg: AppColors.ink, fontSize: 12, child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text(s.v('expandAll')),
                const SizedBox(width: 4),
                const Icon(Icons.keyboard_arrow_down, size: 14, color: AppColors.ink),
              ])),
            ],
          ),
        ),
        const SizedBox(height: 16),
        for (int i = 0; i < faqs.length; i++) ...[
          AppCard(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                InkWell(
                  onTap: () => ref.read(openFaqProvider.notifier).state = open == i ? -1 : i,
                  child: Row(
                    children: [
                      Expanded(child: Text(lang == 'ar' ? faqs[i].ar : faqs[i].en, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: AppColors.ink))),
                      const SizedBox(width: 12),
                      AnimatedRotation(
                        turns: open == i ? 0.5 : 0,
                        duration: const Duration(milliseconds: 180),
                        child: const Icon(Icons.keyboard_arrow_down, size: 20, color: AppColors.sub),
                      ),
                    ],
                  ),
                ),
                if (open == i) ...[
                  const SizedBox(height: 12),
                  Text(lang == 'ar' ? faqs[i].aAr : faqs[i].aEn, style: const TextStyle(color: AppColors.sub, height: 1.6, fontSize: 15)),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],
      ],
    );
  }
}

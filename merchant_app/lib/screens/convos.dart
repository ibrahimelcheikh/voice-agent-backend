import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/dashboard_repository.dart';
import '../data/merchant_repository.dart';
import '../data/models.dart';
import '../l10n/strings.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class ConvosScreen extends ConsumerStatefulWidget {
  const ConvosScreen({super.key});
  @override
  ConsumerState<ConvosScreen> createState() => _ConvosScreenState();
}

class _ConvosScreenState extends ConsumerState<ConvosScreen> {
  String q = '';

  @override
  Widget build(BuildContext context) {
    final lang = ref.watch(languageProvider);
    final s = S.of(lang);
    final rtl = lang == 'ar';
    ref.watch(refreshTickProvider); // rebuild after pull-to-refresh
    final all = ref.read(merchantRepositoryProvider).conversations();
    final list = all.where((c) => q.isEmpty || c.name.toLowerCase().contains(q.toLowerCase())).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ScreenHeader(title: s.v('convosTitle'), sub: s.v('convosSub')),
        const SizedBox(height: 14),
        _searchField(s, rtl),
        const SizedBox(height: 14),
        Row(children: [
          Pill(
            bg: AppColors.card,
            fg: AppColors.ink,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
            fontSize: 14,
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.event_available, size: 16, color: AppColors.ink),
              const SizedBox(width: 6),
              Text(s.v('ordersOnly')),
            ]),
          ),
          const SizedBox(width: 10),
          InkWell(
            onTap: () => showDialog(context: context, builder: (_) => _DateRangeDialog(s: s, rtl: rtl)),
            borderRadius: BorderRadius.circular(999),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
              decoration: BoxDecoration(color: AppColors.card, borderRadius: BorderRadius.circular(999)),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.calendar_today_outlined, size: 16, color: AppColors.ink),
                const SizedBox(width: 6),
                Text(s.v('dateRange'), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: AppColors.ink)),
                const SizedBox(width: 6),
                const Icon(Icons.keyboard_arrow_down, size: 15, color: AppColors.ink),
              ]),
            ),
          ),
        ]),
        const SizedBox(height: 14),
        for (final c in list) ...[
          _ConvoCard(c: c, s: s, rtl: rtl, lang: lang),
          const SizedBox(height: 14),
        ],
      ],
    );
  }

  Widget _searchField(S s, bool rtl) {
    return TextField(
      onChanged: (v) => setState(() => q = v),
      style: const TextStyle(fontSize: 15, color: AppColors.ink),
      decoration: InputDecoration(
        hintText: s.v('searchConvos'),
        hintStyle: const TextStyle(color: AppColors.sub),
        prefixIcon: const Icon(Icons.search, color: AppColors.sub, size: 20),
        filled: true,
        fillColor: AppColors.card,
        contentPadding: const EdgeInsets.symmetric(vertical: 15),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
      ),
    );
  }
}

class _ConvoCard extends StatefulWidget {
  final Convo c;
  final S s;
  final bool rtl;
  final String lang;
  const _ConvoCard({required this.c, required this.s, required this.rtl, required this.lang});
  @override
  State<_ConvoCard> createState() => _ConvoCardState();
}

class _ConvoCardState extends State<_ConvoCard> {
  late bool open = widget.c.tag == 'booked';

  @override
  Widget build(BuildContext context) {
    final c = widget.c;
    final s = widget.s;
    final tag = _tagStyle(c.tag);
    return AppCard(
      padding: const EdgeInsets.all(18),
      border: c.urgent ? Border.all(color: AppColors.rose, width: 1.5) : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: () => setState(() => open = !open),
            child: Row(
              children: [
                IconBox(icon: tag.$3, bg: tag.$1, fg: tag.$2, iconSize: 15),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(c.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: AppColors.ink)),
                      Text('${c.phone} · ${c.time}', style: const TextStyle(color: AppColors.sub, fontSize: 13)),
                    ],
                  ),
                ),
                Pill(
                  bg: c.lang == 'ar' ? AppColors.blueSoft : AppColors.cardAlt,
                  fg: c.lang == 'ar' ? AppColors.blueDeep : AppColors.sub,
                  fontSize: 11,
                  child: Text(c.lang == 'ar' ? 'ع' : 'EN'),
                ),
                const SizedBox(width: 8),
                AnimatedRotation(
                  turns: open ? 0.5 : 0,
                  duration: const Duration(milliseconds: 180),
                  child: const Icon(Icons.keyboard_arrow_down, size: 20, color: AppColors.sub),
                ),
              ],
            ),
          ),
          if (open) ...[
            const SizedBox(height: 14),
            if (c.treatment != null)
              Container(
                padding: const EdgeInsets.all(16),
                margin: const EdgeInsets.only(bottom: 14),
                decoration: BoxDecoration(color: AppColors.greenSoft, borderRadius: BorderRadius.circular(16)),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(c.treatment!, style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink)),
                    Text(money(c.price ?? 0, widget.lang),
                        style: const TextStyle(fontWeight: FontWeight.w900, color: AppColors.green)),
                  ],
                ),
              ),
            if (c.urgent)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Pill(
                    bg: AppColors.amberSoft,
                    fg: AppColors.amber,
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.warning_amber_rounded, size: 14, color: AppColors.amber),
                      const SizedBox(width: 5),
                      Text(s.v('transferredUrgent')),
                    ]),
                  ),
                ),
              ),
            Text(c.summary, style: const TextStyle(color: AppColors.sub, height: 1.6, fontSize: 15)),
            if ((c.transcript ?? '').isNotEmpty && c.transcript != c.summary)
              _TranscriptExpander(text: c.transcript!, label: s.v('viewTranscript')),
            const SizedBox(height: 14),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                PillButton.dark('${s.v('play')}${c.dur != "—" ? ' (${c.dur})' : ''}', icon: Icons.play_arrow),
                Pill(
                  bg: AppColors.cardAlt,
                  fg: AppColors.ink,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  child: Text('${s.v('sentiment')}: ${c.sentiment}'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  (Color, Color, IconData) _tagStyle(String tag) {
    switch (tag) {
      case 'booked':
        return (AppColors.greenSoft, AppColors.green, Icons.event_available);
      case 'msg':
        return (AppColors.blueSoft, AppColors.blue, Icons.chat_bubble_outline);
      default:
        return (AppColors.cardAlt, AppColors.sub, Icons.call_outlined);
    }
  }
}

/// Date-range picker modal (July 2026, 17–24 highlighted) — matches the design.
class _DateRangeDialog extends StatelessWidget {
  final S s;
  final bool rtl;
  const _DateRangeDialog({required this.s, required this.rtl});

  @override
  Widget build(BuildContext context) {
    final days = rtl
        ? ['أحد', 'إثنين', 'ثلاثاء', 'أربعاء', 'خميس', 'جمعة', 'سبت']
        : ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    // build 35-cell grid: 3 leading dim (28,29,30), then 1..31, then trailing dim
    final cells = <(int, bool)>[];
    const leading = [28, 29, 30];
    int n = 1;
    for (int i = 0; i < 35; i++) {
      if (i < 3) {
        cells.add((leading[i], true));
      } else if (n <= 31) {
        cells.add((n++, false));
      } else {
        cells.add((n++ - 31, true));
      }
    }

    return Dialog(
      backgroundColor: AppColors.card,
      insetPadding: const EdgeInsets.all(20),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 380),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // range fields
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(14)),
                child: Row(children: [
                  Expanded(child: _rangeField(rtl ? '١٧ يوليو ٢٠٢٦' : 'Jul 17, 2026', selected: true)),
                  const SizedBox(width: 10),
                  Expanded(child: _rangeField(rtl ? '٢٤ يوليو ٢٠٢٦' : 'Jul 24, 2026', selected: false)),
                ]),
              ),
              const SizedBox(height: 18),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _arrowBtn(rtl ? Icons.chevron_right : Icons.chevron_left),
                  Text(rtl ? 'يوليو ٢٠٢٦' : 'July 2026', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17, color: AppColors.ink)),
                  _arrowBtn(rtl ? Icons.chevron_left : Icons.chevron_right),
                ],
              ),
              const SizedBox(height: 14),
              GridView.count(
                crossAxisCount: 7,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                childAspectRatio: 1.3,
                children: [
                  for (final d in days)
                    Center(child: Text(d, style: const TextStyle(color: AppColors.sub, fontSize: 12, fontWeight: FontWeight.w700))),
                ],
              ),
              GridView.count(
                crossAxisCount: 7,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 2,
                crossAxisSpacing: 2,
                childAspectRatio: 1.1,
                children: [
                  for (final c in cells)
                    _dayCell(c.$1, dim: c.$2, sel: !c.$2 && c.$1 >= 17 && c.$1 <= 24, edge: !c.$2 && (c.$1 == 17 || c.$1 == 24)),
                ],
              ),
              const SizedBox(height: 18),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  _footBtn(s.v('cancel'), bg: AppColors.cardAlt, fg: AppColors.ink, onTap: () => Navigator.pop(context)),
                  const SizedBox(width: 10),
                  _footBtn(s.v('apply'), bg: AppColors.amber, fg: Colors.white, onTap: () => Navigator.pop(context)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _rangeField(String label, {required bool selected}) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(10),
          border: selected ? Border.all(color: AppColors.blue, width: 1.5) : null,
        ),
        alignment: Alignment.center,
        child: Text(label, style: TextStyle(fontWeight: FontWeight.w800, color: selected ? AppColors.ink : AppColors.sub)),
      );

  Widget _arrowBtn(IconData icon) => Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(12)),
        child: Icon(icon, size: 18, color: AppColors.ink),
      );

  Widget _dayCell(int d, {required bool dim, required bool sel, required bool edge}) => Container(
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: sel ? AppColors.amber : Colors.transparent,
          borderRadius: BorderRadius.circular(sel ? 999 : 0),
        ),
        child: Text('$d',
            style: TextStyle(
              color: dim ? const Color(0xFFCFC7B8) : (sel ? Colors.white : AppColors.ink),
              fontWeight: edge ? FontWeight.w800 : FontWeight.w600,
              fontSize: 15,
            )),
      );

  Widget _footBtn(String label, {required Color bg, required Color fg, required VoidCallback onTap}) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(999),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 26, vertical: 12),
          decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
          child: Text(label, style: TextStyle(fontWeight: FontWeight.w800, color: fg)),
        ),
      );
}

/// Collapsible full call transcript shown under the AI summary.
class _TranscriptExpander extends StatefulWidget {
  const _TranscriptExpander({required this.text, required this.label});
  final String text;
  final String label;
  @override
  State<_TranscriptExpander> createState() => _TranscriptExpanderState();
}

class _TranscriptExpanderState extends State<_TranscriptExpander> {
  bool open = false;
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 10),
        InkWell(
          onTap: () => setState(() => open = !open),
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(open ? Icons.expand_less : Icons.expand_more, size: 18, color: AppColors.blue),
              const SizedBox(width: 4),
              Text(widget.label, style: const TextStyle(color: AppColors.blue, fontWeight: FontWeight.w800, fontSize: 14)),
            ]),
          ),
        ),
        if (open)
          Container(
            width: double.infinity,
            margin: const EdgeInsets.only(top: 6),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(12)),
            child: Text(widget.text, style: const TextStyle(color: AppColors.ink, height: 1.55, fontSize: 14.5)),
          ),
      ],
    );
  }
}

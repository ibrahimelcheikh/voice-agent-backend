import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../l10n/strings.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class OverviewScreen extends ConsumerWidget {
  const OverviewScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(languageProvider);
    final s = S.of(lang);
    final rtl = lang == 'ar';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // greeting block
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 8, 4, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 6),
              Text(s.v('greeting'),
                  style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w900, letterSpacing: -0.5, color: AppColors.ink)),
              const SizedBox(height: 10),
              Row(children: [
                const Icon(Icons.access_time, size: 17, color: AppColors.sub),
                const SizedBox(width: 8),
                Text(s.v('todayIs'), style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w600)),
              ]),
              const SizedBox(height: 14),
              Text.rich(
                TextSpan(
                  style: const TextStyle(fontSize: 27, fontWeight: FontWeight.w800, color: AppColors.ink, height: 1.3),
                  children: [
                    TextSpan(text: '${s.v('earned')} '),
                    TextSpan(text: money(184500, lang), style: const TextStyle(color: AppColors.blue)),
                    TextSpan(text: ' ${s.v('earnedTail')}'),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        KpiCard(icon: Icons.access_time, bg: AppColors.blueSoft, fg: AppColors.blue, label: s.v('staffHours'), value: s.v('val34hours'), sub: s.v('thisMonth')),
        const SizedBox(height: 16),
        KpiCard(icon: Icons.phone_callback_outlined, bg: AppColors.amberSoft, fg: AppColors.amber, label: s.v('extraCalls'), value: s.v('val118'), sub: s.v('thisMonth')),
        const SizedBox(height: 16),
        KpiCard(icon: Icons.event_available, bg: AppColors.greenSoft, fg: AppColors.green, label: s.v('bookings'), value: s.v('val243'), sub: s.v('thisMonth')),
        const SizedBox(height: 16),
        _PopularTimes(s: s, rtl: rtl),
        const SizedBox(height: 16),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          child: Text(s.v('optimize'), style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w700, fontSize: 15)),
        ),
        const SizedBox(height: 16),
        _TipCard(s: s),
        const SizedBox(height: 16),
        _RecentActivity(s: s, lang: lang, rtl: rtl),
      ],
    );
  }
}

class _PopularTimes extends StatelessWidget {
  final S s;
  final bool rtl;
  const _PopularTimes({required this.s, required this.rtl});

  @override
  Widget build(BuildContext context) {
    const heights = <double>[30, 44, 72, 90, 64, 52, 40, 34, 30];
    return AppCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(s.v('popular'), style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: AppColors.ink)),
              Pill(bg: AppColors.cardAlt, fg: AppColors.ink, child: Text(s.v('saturday'))),
            ],
          ),
          const SizedBox(height: 22),
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: Pill(bg: AppColors.amberSoft, fg: AppColors.amber, child: Text(s.v('live'))),
          ),
          const SizedBox(height: 22),
          SizedBox(
            height: 90,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                for (int i = 0; i < heights.length; i++) ...[
                  if (i > 0) const SizedBox(width: 10),
                  Expanded(
                    child: Container(
                      height: heights[i],
                      decoration: BoxDecoration(
                        color: i == 3 ? AppColors.blue : (i < 3 ? AppColors.ink : AppColors.line),
                        borderRadius: const BorderRadius.only(
                          topLeft: Radius.circular(10),
                          topRight: Radius.circular(10),
                          bottomLeft: Radius.circular(4),
                          bottomRight: Radius.circular(4),
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 8),
          const Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('1PM', style: TextStyle(color: AppColors.sub, fontSize: 13, fontWeight: FontWeight.w600)),
              Text('4PM', style: TextStyle(color: AppColors.sub, fontSize: 13, fontWeight: FontWeight.w600)),
              Text('7PM', style: TextStyle(color: AppColors.sub, fontSize: 13, fontWeight: FontWeight.w600)),
              Text('9PM', style: TextStyle(color: AppColors.sub, fontSize: 13, fontWeight: FontWeight.w600)),
            ],
          ),
        ],
      ),
    );
  }
}

class _TipCard extends ConsumerWidget {
  final S s;
  const _TipCard({required this.s});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppCard(
      padding: const EdgeInsets.all(20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const IconBox(icon: Icons.auto_awesome, bg: AppColors.blueSoft, fg: AppColors.blue),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 2),
                Text(s.v('tipTitle'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppColors.ink)),
                const SizedBox(height: 6),
                Text(s.v('tipBody'), style: const TextStyle(color: AppColors.sub, height: 1.5)),
                const SizedBox(height: 12),
                InkWell(
                  onTap: () => goTo(ref, 'settings'),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(s.v('configure'), style: const TextStyle(color: AppColors.blue, fontWeight: FontWeight.w800, fontSize: 15)),
                      const SizedBox(width: 4),
                      const Icon(Icons.arrow_forward, size: 15, color: AppColors.blue),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _RecentActivity extends ConsumerWidget {
  final S s;
  final String lang;
  final bool rtl;
  const _RecentActivity({required this.s, required this.lang, required this.rtl});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rows = [
      _Row(Icons.event_available, AppColors.greenSoft, AppColors.green, 'Nour A.', '${s.v('booked')} · ${s.v('min12')}', money(2200, lang)),
      _Row(Icons.call_outlined, AppColors.cardAlt, AppColors.sub, '+966 50 771 3320', '${s.v('callCompleted')} · ${s.v('min40')}', ''),
      _Row(Icons.chat_bubble_outline, AppColors.blueSoft, AppColors.blue, 'Layla M.', '${s.v('msg')} · ${s.v('hr1')}', ''),
      _Row(Icons.call_outlined, AppColors.cardAlt, AppColors.sub, 'Sara K.', '${s.v('callCompleted')} · ${s.v('hrs3')}', money(400, lang)),
    ];
    return AppCard(
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
                    Text(s.v('recent'), style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: AppColors.ink)),
                    const SizedBox(height: 6),
                    Text(s.v('recentSub'), style: const TextStyle(color: AppColors.sub, height: 1.45)),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              InkWell(
                onTap: () => goTo(ref, 'convos'),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  decoration: BoxDecoration(color: AppColors.blueSoft, borderRadius: BorderRadius.circular(999)),
                  child: Text(s.v('viewAll'), style: const TextStyle(color: AppColors.blueDeep, fontWeight: FontWeight.w800)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          for (int i = 0; i < rows.length; i++)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                border: i == 0 ? null : const Border(top: BorderSide(color: AppColors.line)),
              ),
              child: Row(
                children: [
                  IconBox(icon: rows[i].icon, bg: rows[i].bg, fg: rows[i].fg, iconSize: 20),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(rows[i].title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: AppColors.ink)),
                        Text(rows[i].meta,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: AppColors.sub, fontSize: 13.5)),
                      ],
                    ),
                  ),
                  if (rows[i].right.isNotEmpty)
                    Text(rows[i].right, style: const TextStyle(fontWeight: FontWeight.w900, color: AppColors.green, fontSize: 17)),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _Row {
  final IconData icon;
  final Color bg;
  final Color fg;
  final String title;
  final String meta;
  final String right;
  _Row(this.icon, this.bg, this.fg, this.title, this.meta, this.right);
}

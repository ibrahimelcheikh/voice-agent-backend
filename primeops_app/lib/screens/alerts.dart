import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/ops_repository.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class AlertsScreen extends ConsumerWidget {
  const AlertsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(alertFilterProvider);
    final all = ref.read(opsRepositoryProvider).alerts();
    final list = all.where((a) => filter == 'all' || a.sev == filter).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Head(title: 'Alerts', sub: 'System health and urgent events across all merchants.'),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final f in const [['all', 'All'], ['critical', 'Critical'], ['warning', 'Warning'], ['info', 'Info']])
            _filterChip(ref, f[0], f[1], filter == f[0]),
        ]),
        const SizedBox(height: 18),
        for (final a in list) ...[
          AppCard(
            padding: const EdgeInsets.all(20),
            border: Border(left: BorderSide(color: sevMap(a.sev).fg, width: 4)),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                IconBox(icon: sevMap(a.sev).icon, bg: sevMap(a.sev).bg, fg: sevMap(a.sev).fg),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(spacing: 8, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
                        Text(a.title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: AppColors.ink)),
                        Pill(bg: sevMap(a.sev).bg, fg: sevMap(a.sev).fg, fontSize: 11, child: Text(sevMap(a.sev).label)),
                      ]),
                      const SizedBox(height: 4),
                      Text('${a.merchant} · ${a.time}', style: const TextStyle(color: AppColors.sub, fontSize: 13.5)),
                      const SizedBox(height: 8),
                      Text(a.body, style: const TextStyle(color: AppColors.ink, height: 1.55, fontSize: 14.5)),
                      const SizedBox(height: 14),
                      Row(children: [
                        PillButton.primary('Investigate'),
                        const SizedBox(width: 10),
                        PillButton.ghost('Dismiss'),
                      ]),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],
      ],
    );
  }

  Widget _filterChip(WidgetRef ref, String k, String label, bool on) {
    return InkWell(
      onTap: () => ref.read(alertFilterProvider.notifier).state = k,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
        decoration: BoxDecoration(color: on ? AppColors.ink : AppColors.card, borderRadius: BorderRadius.circular(999)),
        child: Text(label, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: on ? Colors.white : AppColors.ink)),
      ),
    );
  }
}

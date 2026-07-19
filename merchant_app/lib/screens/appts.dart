import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/merchant_repository.dart';
import '../data/models.dart';
import '../l10n/strings.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class ApptsScreen extends ConsumerWidget {
  const ApptsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(languageProvider);
    final s = S.of(lang);
    final appts = ref.read(merchantRepositoryProvider).appointments();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ScreenHeader(title: s.v('apptsTitle'), sub: s.v('apptsSub')),
        const SizedBox(height: 14),
        AppCard(
          color: AppColors.cardAlt,
          padding: const EdgeInsets.all(16),
          border: Border.all(color: AppColors.line, width: 1.5, style: BorderStyle.solid),
          child: Row(
            children: [
              const Icon(Icons.calendar_today_outlined, size: 20, color: AppColors.sub),
              const SizedBox(width: 12),
              Expanded(child: Text(s.v('calDim'), style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w600, height: 1.4))),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
          child: Text(s.v('upcoming'), style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w800, fontSize: 15)),
        ),
        for (final a in appts) ...[
          _apptCard(a, s, lang),
          const SizedBox(height: 14),
        ],
      ],
    );
  }

  Widget _apptCard(Appt a, S s, String lang) {
    return AppCard(
      padding: const EdgeInsets.all(18),
      child: Row(
        children: [
          Container(
            width: 58,
            height: 62,
            decoration: BoxDecoration(color: AppColors.blueSoft, borderRadius: BorderRadius.circular(16)),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(loc(a.day, lang), style: const TextStyle(color: AppColors.blueDeep, fontWeight: FontWeight.w800, fontSize: 12)),
                Text(a.date, style: const TextStyle(color: AppColors.blueDeep, fontWeight: FontWeight.w900, fontSize: 22, height: 1)),
              ],
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(a.name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17, color: AppColors.ink)),
                const SizedBox(height: 2),
                Text(loc(a.svc, lang), style: const TextStyle(color: AppColors.ink, fontSize: 15)),
                const SizedBox(height: 6),
                Row(children: [
                  Pill(
                    bg: AppColors.cardAlt,
                    fg: AppColors.sub,
                    fontSize: 12,
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.access_time, size: 12, color: AppColors.sub),
                      const SizedBox(width: 5),
                      Text(a.time),
                    ]),
                  ),
                  const SizedBox(width: 8),
                  Pill(
                    bg: AppColors.greenSoft,
                    fg: AppColors.green,
                    fontSize: 12,
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.auto_awesome, size: 12, color: AppColors.green),
                      const SizedBox(width: 5),
                      Text(a.via),
                    ]),
                  ),
                ]),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

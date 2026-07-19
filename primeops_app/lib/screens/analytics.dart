import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/ops_repository.dart';
import '../theme/tokens.dart';
import '../widgets/charts.dart';
import '../widgets/ui.dart';

class AnalyticsScreen extends ConsumerWidget {
  const AnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final desktop = MediaQuery.of(context).size.width >= 900;
    final repo = ref.read(opsRepositoryProvider);
    final byCalls = repo.merchants().where((m) => m.calls > 0).toList()..sort((a, b) => b.calls - a.calls);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Head(
          title: 'Analytics',
          sub: 'Cross-merchant performance.',
          right: Pill(bg: AppColors.cardAlt, fg: AppColors.ink, child: Row(mainAxisSize: MainAxisSize.min, children: const [
            Icon(Icons.access_time, size: 14, color: AppColors.ink),
            SizedBox(width: 5),
            Text('Last 30 days'),
          ])),
        ),
        ResponsiveGrid(minItemWidth: desktop ? 230 : 150, children: const [
          Kpi(icon: Icons.call_outlined, bg: AppColors.amberSoft, fg: AppColors.amber, label: 'Total calls', value: '6,180', sub: '+18% vs prev'),
          Kpi(icon: Icons.event_available, bg: AppColors.greenSoft, fg: AppColors.green, label: 'Bookings', value: '694', sub: '38% conversion'),
          Kpi(icon: Icons.access_time, bg: AppColors.blueSoft, fg: AppColors.blue, label: 'Staff hours saved', value: '182', sub: 'Across fleet'),
          Kpi(icon: Icons.attach_money, bg: AppColors.violetSoft, fg: AppColors.violet, label: 'Attributed revenue', value: '\$486k', sub: 'Booked treatments'),
        ]),
        const SizedBox(height: 20),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Calls by merchant', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.ink)),
              const SizedBox(height: 14),
              HBarChartView(rows: [for (final m in byCalls) MapEntry(m.name, m.calls)]),
            ],
          ),
        ),
        const SizedBox(height: 20),
        ResponsiveGrid(minItemWidth: desktop ? 330 : 260, children: [
          AppCard(
            padding: const EdgeInsets.all(22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text('Booking channel', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.ink)),
                SizedBox(height: 14),
                DonutChartView(
                  segments: [MapEntry(58, AppColors.blue), MapEntry(30, AppColors.green), MapEntry(12, AppColors.amber)],
                  labels: ['Voice', 'WhatsApp', 'Web'],
                ),
              ],
            ),
          ),
          AppCard(
            padding: const EdgeInsets.all(22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Fleet call volume', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.ink)),
                const SizedBox(height: 14),
                LineChartView(data: repo.fleetVolume()),
              ],
            ),
          ),
        ]),
      ],
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/ops_repository.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/charts.dart';
import '../widgets/ui.dart';

class OpsOverviewScreen extends ConsumerWidget {
  const OpsOverviewScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final desktop = MediaQuery.of(context).size.width >= 900;
    final repo = ref.read(opsRepositoryProvider);
    final merchants = repo.merchants();
    final totalCalls = merchants.fold<int>(0, (a, m) => a + m.calls);
    final totalBookings = merchants.fold<int>(0, (a, m) => a + m.bookings);
    final mrr = merchants.fold<int>(0, (a, m) => a + m.mrr);
    final live = merchants.where((m) => m.status == 'live').length;
    final alerts = repo.alerts();
    final tickets = repo.tickets();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Head(title: 'Good afternoon, Ibrahim', sub: "Here's how the fleet is doing today."),
        ResponsiveGrid(minItemWidth: desktop ? 230 : 150, children: [
          Kpi(icon: Icons.storefront_outlined, bg: AppColors.blueSoft, fg: AppColors.blue, label: 'Active merchants', value: '$live', sub: '${merchants.length} total'),
          Kpi(icon: Icons.call_outlined, bg: AppColors.amberSoft, fg: AppColors.amber, label: 'Calls (fleet)', value: fmtInt(totalCalls), sub: 'This month'),
          Kpi(icon: Icons.event_available, bg: AppColors.greenSoft, fg: AppColors.green, label: 'Bookings (fleet)', value: fmtInt(totalBookings), sub: 'This month'),
          Kpi(icon: Icons.attach_money, bg: AppColors.violetSoft, fg: AppColors.violet, label: 'MRR', value: '\$${fmtInt(mrr)}', sub: 'Recurring'),
        ]),
        const SizedBox(height: 20),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text('Fleet call volume', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w900, color: AppColors.ink)),
                        SizedBox(height: 4),
                        Text('All merchants, last 28 days', style: TextStyle(color: AppColors.sub)),
                      ],
                    ),
                  ),
                  Pill(bg: AppColors.greenSoft, fg: AppColors.green, child: Row(mainAxisSize: MainAxisSize.min, children: const [
                    Icon(Icons.trending_up, size: 14, color: AppColors.green),
                    SizedBox(width: 4),
                    Text('+18%'),
                  ])),
                ],
              ),
              const SizedBox(height: 16),
              LineChartView(data: repo.fleetVolume()),
            ],
          ),
        ),
        const SizedBox(height: 20),
        ResponsiveGrid(minItemWidth: desktop ? 330 : 260, children: [
          AppCard(
            padding: const EdgeInsets.all(22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Active alerts', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.ink)),
                    InkWell(onTap: () => goTo(ref, 'alerts'), child: const Text('View all', style: TextStyle(color: AppColors.blue, fontWeight: FontWeight.w800, fontSize: 14))),
                  ],
                ),
                for (int i = 0; i < 3 && i < alerts.length; i++)
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: const BoxDecoration(border: Border(top: BorderSide(color: AppColors.line))),
                    child: Row(children: [
                      IconBox(icon: sevMap(alerts[i].sev).icon, bg: sevMap(alerts[i].sev).bg, fg: sevMap(alerts[i].sev).fg, size: 38, iconSize: 18),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(alerts[i].title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.ink)),
                            Text('${alerts[i].merchant} · ${alerts[i].time}', style: const TextStyle(color: AppColors.sub, fontSize: 13)),
                          ],
                        ),
                      ),
                    ]),
                  ),
              ],
            ),
          ),
          AppCard(
            padding: const EdgeInsets.all(22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Open tickets', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.ink)),
                    InkWell(onTap: () => goTo(ref, 'tickets'), child: const Text('View all', style: TextStyle(color: AppColors.blue, fontWeight: FontWeight.w800, fontSize: 14))),
                  ],
                ),
                for (final tk in tickets.where((t) => t.status != 'resolved').take(3))
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: const BoxDecoration(border: Border(top: BorderSide(color: AppColors.line))),
                    child: Row(children: [
                      const IconBox(icon: Icons.confirmation_number_outlined, bg: AppColors.cardAlt, fg: AppColors.sub, size: 38, iconSize: 18),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(tk.subject, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.ink)),
                            Text('${tk.merchant} · ${tk.id}', style: const TextStyle(color: AppColors.sub, fontSize: 13)),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Pill(bg: ticketStatus(tk.status).bg, fg: ticketStatus(tk.status).fg, child: Text(ticketStatus(tk.status).label)),
                    ]),
                  ),
              ],
            ),
          ),
        ]),
      ],
    );
  }
}

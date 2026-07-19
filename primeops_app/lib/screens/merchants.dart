import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models.dart';
import '../data/ops_repository.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class MerchantsScreen extends ConsumerStatefulWidget {
  const MerchantsScreen({super.key});
  @override
  ConsumerState<MerchantsScreen> createState() => _MerchantsScreenState();
}

class _MerchantsScreenState extends ConsumerState<MerchantsScreen> {
  String q = '';

  @override
  Widget build(BuildContext context) {
    final desktop = MediaQuery.of(context).size.width >= 900;
    final active = ref.watch(activeMerchantProvider);
    final all = ref.read(opsRepositoryProvider).merchants();

    if (active != null) return _MerchantDetail(m: active, desktop: desktop);

    final list = all.where((m) => q.isEmpty || m.name.toLowerCase().contains(q.toLowerCase()) || m.city.toLowerCase().contains(q.toLowerCase())).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Head(
          title: 'Merchants',
          sub: '${all.length} clients across the Gulf.',
          right: PillButton.primary('Add merchant', icon: Icons.add),
        ),
        TextField(
          onChanged: (v) => setState(() => q = v),
          style: const TextStyle(fontSize: 15, color: AppColors.ink),
          decoration: InputDecoration(
            hintText: 'Search merchants…',
            hintStyle: const TextStyle(color: AppColors.sub),
            prefixIcon: const Icon(Icons.search, color: AppColors.sub, size: 20),
            filled: true,
            fillColor: AppColors.card,
            contentPadding: const EdgeInsets.symmetric(vertical: 14),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
          ),
        ),
        const SizedBox(height: 18),
        ResponsiveGrid(minItemWidth: desktop ? 330 : 280, children: [
          for (final m in list) _merchantCard(m),
        ]),
      ],
    );
  }

  Widget _merchantCard(Merchant m) {
    final sp = statusPill(m.status);
    final hc = m.health > 80 ? AppColors.green : m.health > 50 ? AppColors.amber : AppColors.rose;
    return AppCard(
      padding: const EdgeInsets.all(20),
      onTap: () => ref.read(activeMerchantProvider.notifier).state = m,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Container(
              width: 46, height: 46,
              decoration: BoxDecoration(color: AppColors.blueSoft, borderRadius: BorderRadius.circular(13)),
              alignment: Alignment.center,
              child: Text(m.name[0], style: const TextStyle(color: AppColors.blueDeep, fontWeight: FontWeight.w900, fontSize: 18)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(m.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: AppColors.ink)),
                  Row(children: [
                    const Icon(Icons.location_on_outlined, size: 12, color: AppColors.sub),
                    const SizedBox(width: 4),
                    Flexible(child: Text('${m.city} · ${m.type}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: AppColors.sub, fontSize: 13))),
                  ]),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Pill(bg: sp.bg, fg: sp.fg, child: Text(sp.label)),
          ]),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: MiniStat(label: 'Calls', value: fmtInt(m.calls))),
            const SizedBox(width: 10),
            Expanded(child: MiniStat(label: 'Bookings', value: fmtInt(m.bookings))),
            const SizedBox(width: 10),
            Expanded(child: MiniStat(label: 'Plan', value: m.plan)),
          ]),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: Container(
                height: 8,
                decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(999)),
                child: FractionallySizedBox(
                  alignment: AlignmentDirectional.centerStart,
                  widthFactor: m.health / 100,
                  child: Container(decoration: BoxDecoration(color: hc, borderRadius: BorderRadius.circular(999))),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Text(m.health > 0 ? '${m.health}% health' : 'Setup', style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: AppColors.sub)),
          ]),
        ],
      ),
    );
  }
}

class _MerchantDetail extends ConsumerWidget {
  final Merchant m;
  final bool desktop;
  const _MerchantDetail({required this.m, required this.desktop});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sp = statusPill(m.status);
    final rows = [
      ['Languages', m.langs.map((x) => x.toUpperCase()).join(' · ')],
      ['Voice', m.langs.contains('ar') ? 'Reem (Khaleeji) + Marissa' : 'Marissa'],
      ['Channels', 'Voice · WhatsApp'],
      ['Cal.com', 'Connected'],
      ['Plan', m.plan],
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        BackLink(label: 'Merchants', onTap: () => ref.read(activeMerchantProvider.notifier).state = null),
        const SizedBox(height: 18),
        Wrap(
          spacing: 16,
          runSpacing: 12,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Container(
              width: 60, height: 60,
              decoration: BoxDecoration(color: AppColors.blueSoft, borderRadius: BorderRadius.circular(16)),
              alignment: Alignment.center,
              child: Text(m.name[0], style: const TextStyle(color: AppColors.blueDeep, fontWeight: FontWeight.w900, fontSize: 24)),
            ),
            ConstrainedBox(
              constraints: const BoxConstraints(minWidth: 180),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(m.name, style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w900, color: AppColors.ink)),
                  const SizedBox(height: 4),
                  Row(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.location_on_outlined, size: 14, color: AppColors.sub),
                    const SizedBox(width: 6),
                    Text('${m.city} · ${m.type} · ${m.plan}', style: const TextStyle(color: AppColors.sub)),
                  ]),
                ],
              ),
            ),
            Pill(bg: sp.bg, fg: sp.fg, child: Text(sp.label)),
            PillButton.primary('View as merchant', icon: Icons.visibility_outlined, onTap: () => ref.read(merchantViewProvider.notifier).state = true),
          ],
        ),
        const SizedBox(height: 18),
        ResponsiveGrid(minItemWidth: desktop ? 220 : 150, children: [
          Kpi(icon: Icons.call_outlined, bg: AppColors.amberSoft, fg: AppColors.amber, label: 'Calls', value: fmtInt(m.calls), sub: 'This month'),
          Kpi(icon: Icons.event_available, bg: AppColors.greenSoft, fg: AppColors.green, label: 'Bookings', value: fmtInt(m.bookings), sub: 'This month'),
          Kpi(icon: Icons.attach_money, bg: AppColors.violetSoft, fg: AppColors.violet, label: 'MRR', value: '\$${m.mrr}', sub: m.plan),
          Kpi(icon: Icons.show_chart, bg: AppColors.blueSoft, fg: AppColors.blue, label: 'Health', value: m.health > 0 ? '${m.health}%' : '—', sub: 'Uptime + sync'),
        ]),
        const SizedBox(height: 18),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Configuration', style: sectionH),
              const SizedBox(height: 4),
              for (int i = 0; i < rows.length; i++)
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 13),
                  decoration: BoxDecoration(border: i == 0 ? null : const Border(top: BorderSide(color: AppColors.line))),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(rows[i][0], style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w600)),
                      Text(rows[i][1], style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink)),
                    ],
                  ),
                ),
              const SizedBox(height: 14),
              PillButton.ghost('Edit configuration', icon: Icons.settings_outlined, fullWidth: true),
            ],
          ),
        ),
      ],
    );
  }
}

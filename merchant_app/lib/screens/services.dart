import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/dashboard_repository.dart';
import '../data/merchant_repository.dart';
import '../data/models.dart';
import '../l10n/strings.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class ServicesScreen extends ConsumerStatefulWidget {
  const ServicesScreen({super.key});
  @override
  ConsumerState<ServicesScreen> createState() => _ServicesScreenState();
}

class _ServicesScreenState extends ConsumerState<ServicesScreen> {
  String q = '';

  @override
  Widget build(BuildContext context) {
    final lang = ref.watch(languageProvider);
    final s = S.of(lang);
    final rtl = lang == 'ar';
    ref.watch(refreshTickProvider); // rebuild after a service edit
    final open = ref.watch(serviceOpenProvider);
    final repo = ref.read(merchantRepositoryProvider);

    if (open != null) {
      final svc = repo.serviceById(open);
      if (svc != null) {
        return _ServiceDetail(svc: svc, s: s, rtl: rtl, lang: lang);
      }
    }

    final services = repo.services();
    final cats = <String>[];
    for (final s in services) {
      if (!cats.contains(s.cat)) cats.add(s.cat);
    }
    final list = services.where((sv) => q.isEmpty || sv.name(lang).contains(q)).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ScreenHeader(title: s.v('servicesTitle'), sub: s.v('servicesSub')),
        const SizedBox(height: 14),
        TextField(
          onChanged: (v) => setState(() => q = v),
          style: const TextStyle(fontSize: 15, color: AppColors.ink),
          decoration: InputDecoration(
            hintText: s.v('searchServices'),
            hintStyle: const TextStyle(color: AppColors.sub),
            prefixIcon: const Icon(Icons.search, color: AppColors.sub, size: 20),
            filled: true,
            fillColor: AppColors.card,
            contentPadding: const EdgeInsets.symmetric(vertical: 15),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
          ),
        ),
        const SizedBox(height: 14),
        // category tabs (display-only, matching the design)
        Container(
          decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AppColors.line))),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (int i = 0; i < cats.length; i++)
                  Padding(
                    padding: const EdgeInsets.only(right: 22),
                    child: Container(
                      padding: const EdgeInsets.only(bottom: 8),
                      decoration: BoxDecoration(
                        border: Border(bottom: BorderSide(color: i == 0 ? AppColors.blue : Colors.transparent, width: 2)),
                      ),
                      child: Text.rich(TextSpan(
                        style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: i == 0 ? AppColors.ink : AppColors.sub),
                        children: [
                          TextSpan(text: cats[i]),
                          TextSpan(
                            text: ' (${services.where((x) => x.cat == cats[i]).length})',
                            style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w600),
                          ),
                        ],
                      )),
                    ),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        _featuredCard(s),
        const SizedBox(height: 14),
        for (final sv in list) ...[
          _serviceCard(sv, s, rtl, lang),
          const SizedBox(height: 14),
        ],
      ],
    );
  }

  Widget _featuredCard(S s) {
    return AppCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const IconBox(icon: Icons.north_east, bg: AppColors.greenSoft, fg: AppColors.green),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Flexible(child: Text(s.v('featured'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.ink))),
                      const SizedBox(width: 10),
                      Pill(bg: AppColors.cardAlt, fg: AppColors.sub, fontSize: 11, child: const Text('2/5')),
                    ]),
                    const SizedBox(height: 6),
                    Text(s.v('featuredSub'), style: const TextStyle(color: AppColors.sub, height: 1.45)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          InkWell(
            onTap: () {},
            borderRadius: BorderRadius.circular(14),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(14)),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                const Icon(Icons.add, size: 18, color: AppColors.ink),
                const SizedBox(width: 8),
                Text(s.v('addRec'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.ink)),
              ]),
            ),
          ),
        ],
      ),
    );
  }

  Widget _serviceCard(Service sv, S s, bool rtl, String lang) {
    return AppCard(
      padding: const EdgeInsets.all(20),
      onTap: () => ref.read(serviceOpenProvider.notifier).state = sv.id,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: Text(sv.name(lang), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18, color: AppColors.ink))),
              Transform.rotate(
                angle: rtl ? 1.5708 : -1.5708,
                child: const Icon(Icons.keyboard_arrow_down, size: 20, color: AppColors.sub),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text('${sv.cat} · ${sv.dur} ${s.v('min')}', style: const TextStyle(color: AppColors.sub, fontSize: 14)),
          const SizedBox(height: 12),
          Row(
            children: [
              Text('${s.v('from')} ${money(sv.price, lang)}',
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 19, color: AppColors.ink)),
              const Spacer(),
              Pill(
                bg: AppColors.greenSoft,
                fg: AppColors.green,
                fontSize: 12,
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.check_circle, size: 13, color: AppColors.green),
                  const SizedBox(width: 5),
                  Text(s.v('book')),
                ]),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ServiceDetail extends ConsumerWidget {
  final Service svc;
  final S s;
  final bool rtl;
  final String lang;
  const _ServiceDetail({required this.svc, required this.s, required this.rtl, required this.lang});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dash = ref.watch(dashboardRepoProvider);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        BackLink(label: s.v('back'), rtl: rtl, onTap: () => ref.read(serviceOpenProvider.notifier).state = null),
        const SizedBox(height: 16),
        Row(children: [
          Expanded(child: Text(svc.name(lang), style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900, color: AppColors.ink))),
          if (dash != null && svc.id.isNotEmpty)
            InkWell(
              onTap: () => _edit(context, ref, dash),
              borderRadius: BorderRadius.circular(999),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                decoration: BoxDecoration(color: AppColors.blueSoft, borderRadius: BorderRadius.circular(999)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.edit, size: 16, color: AppColors.blueDeep),
                  const SizedBox(width: 6),
                  Text(s.v('edit'), style: const TextStyle(color: AppColors.blueDeep, fontWeight: FontWeight.w800)),
                ]),
              ),
            ),
        ]),
        const SizedBox(height: 8),
        Wrap(spacing: 8, runSpacing: 8, children: [
          Pill(bg: AppColors.blueSoft, fg: AppColors.blueDeep, child: Text(svc.cat)),
          Pill(bg: AppColors.cardAlt, fg: AppColors.ink, child: Row(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.timer_outlined, size: 14, color: AppColors.ink),
            const SizedBox(width: 5),
            Text('${svc.dur} ${s.v('min')}'),
          ])),
          Pill(bg: AppColors.greenSoft, fg: AppColors.green, child: Row(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.check_circle, size: 13, color: AppColors.green),
            const SizedBox(width: 5),
            Text(s.v('book')),
          ])),
        ]),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(s.v('about'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: AppColors.ink)),
              const SizedBox(height: 10),
              Text(loc(svc.about, lang), style: const TextStyle(color: AppColors.sub, height: 1.65, fontSize: 15)),
            ],
          ),
        ),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(s.v('tiers'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: AppColors.ink)),
              const SizedBox(height: 4),
              for (int i = 0; i < svc.tiers.length; i++)
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  decoration: BoxDecoration(border: i == 0 ? null : const Border(top: BorderSide(color: AppColors.line))),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(loc(svc.tiers[i].label, lang), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: AppColors.ink)),
                      Text(money(svc.tiers[i].price, lang), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: AppColors.blue)),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        _infoCard(Icons.verified_user_outlined, AppColors.blueSoft, AppColors.blue, s.v('prep'), loc(svc.prep, lang)),
        const SizedBox(height: 16),
        _infoCard(Icons.sentiment_satisfied_alt, AppColors.greenSoft, AppColors.green, s.v('aftercare'), loc(svc.after, lang)),
        const SizedBox(height: 16),
        PillButton(
          label: s.v('bookNow'),
          icon: Icons.event_available,
          bg: AppColors.blue,
          fg: Colors.white,
          fullWidth: true,
          padding: const EdgeInsets.all(16),
          shadow: const [BoxShadow(color: Color(0x442E6BFF), blurRadius: 20, offset: Offset(0, 8))],
        ),
      ],
    );
  }

  Widget _infoCard(IconData icon, Color bg, Color fg, String title, String body) {
    return AppCard(
      padding: const EdgeInsets.all(20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IconBox(icon: icon, bg: bg, fg: fg, iconSize: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: AppColors.ink)),
                const SizedBox(height: 4),
                Text(body, style: const TextStyle(color: AppColors.sub, height: 1.55, fontSize: 14.5)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _edit(BuildContext context, WidgetRef ref, DashboardMerchantRepository dash) {
    final nameC = TextEditingController(text: svc.en);
    final priceC = TextEditingController(text: '${svc.price}');
    showDialog(
      context: context,
      builder: (dctx) => AlertDialog(
        backgroundColor: AppColors.card,
        title: Text('${s.v('edit')} — ${svc.name(lang)}'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: nameC, decoration: InputDecoration(labelText: s.v('fService'))),
          TextField(
            controller: priceC,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Price (SAR)'),
          ),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.of(dctx).pop(), child: Text(s.v('cancel'))),
          FilledButton(
            onPressed: () async {
              Navigator.of(dctx).pop();
              try {
                await dash.updateService(
                  svc.id,
                  name: nameC.text.trim().isEmpty ? null : nameC.text.trim(),
                  price: int.tryParse(priceC.text.trim()),
                );
                ref.read(refreshTickProvider.notifier).state++;
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
                }
              }
            },
            child: Text(s.v('save')),
          ),
        ],
      ),
    );
  }
}

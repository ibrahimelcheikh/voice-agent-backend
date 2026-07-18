import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/ops_repository.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/charts.dart';
import '../widgets/ui.dart';

const _arDigits = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];

/// "View as merchant" — a compact preview of the merchant app experience,
/// opened from the console for a selected tenant. Has its own EN/AR toggle.
class MerchantView extends ConsumerWidget {
  const MerchantView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(merchantViewLangProvider);
    final rtl = lang == 'ar';
    final vol = ref.read(opsRepositoryProvider).fleetVolume();

    String money(int n) => rtl ? '${_ar(_grp(n))} ريال' : 'SAR ${_grp(n)}';

    return Directionality(
      textDirection: rtl ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        backgroundColor: AppColors.bg,
        body: SafeArea(
          bottom: false,
          child: Column(
            children: [
              // banner
              Container(
                color: AppColors.ink,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                child: Row(children: [
                  const Icon(Icons.visibility_outlined, size: 16, color: Colors.white),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      rtl ? 'أنت تشاهد كتاجر — عيادة ديفينيا' : 'Viewing as merchant — Divinia Clinic',
                      style: const TextStyle(color: Colors.white, fontSize: 13.5, fontWeight: FontWeight.w700),
                    ),
                  ),
                  InkWell(
                    onTap: () => ref.read(merchantViewProvider.notifier).state = false,
                    borderRadius: BorderRadius.circular(999),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(999)),
                      child: Row(mainAxisSize: MainAxisSize.min, children: [
                        const Icon(Icons.arrow_back, size: 14, color: Colors.white),
                        const SizedBox(width: 6),
                        Text(rtl ? 'خروج' : 'Exit', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12.5)),
                      ]),
                    ),
                  ),
                ]),
              ),
              // header
              Container(
                decoration: const BoxDecoration(color: AppColors.card, border: Border(bottom: BorderSide(color: AppColors.line))),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(children: [
                  Image.asset('assets/logo-mark.png', width: 34, height: 34),
                  const SizedBox(width: 9),
                  Text.rich(TextSpan(
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18),
                    children: const [
                      TextSpan(text: 'Atlas', style: TextStyle(color: AppColors.ink)),
                      TextSpan(text: 'Prime', style: TextStyle(color: AppColors.blue)),
                      TextSpan(text: 'X', style: TextStyle(color: AppColors.blueDeep)),
                    ],
                  )),
                  const Spacer(),
                  InkWell(
                    onTap: () => ref.read(merchantViewLangProvider.notifier).state = rtl ? 'en' : 'ar',
                    borderRadius: BorderRadius.circular(999),
                    child: Container(
                      height: 40,
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      decoration: BoxDecoration(color: AppColors.blueSoft, borderRadius: BorderRadius.circular(999)),
                      child: Row(mainAxisSize: MainAxisSize.min, children: [
                        const Icon(Icons.language, size: 16, color: AppColors.blueDeep),
                        const SizedBox(width: 7),
                        Text(rtl ? 'EN' : 'ع', style: const TextStyle(color: AppColors.blueDeep, fontWeight: FontWeight.w800, fontSize: 14)),
                      ]),
                    ),
                  ),
                ]),
              ),
              Expanded(
                child: SingleChildScrollView(
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 640),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Padding(
                              padding: const EdgeInsets.all(4),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const SizedBox(height: 6),
                                  Text(rtl ? 'مساء الخير، ديفينيا' : 'Good afternoon, Divinia',
                                      style: const TextStyle(fontSize: 27, fontWeight: FontWeight.w900, color: AppColors.ink)),
                                  const SizedBox(height: 8),
                                  Text.rich(TextSpan(
                                    style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppColors.ink, height: 1.3),
                                    children: [
                                      TextSpan(text: rtl ? 'لقد حجزت ' : "You've booked "),
                                      TextSpan(text: money(184500), style: const TextStyle(color: AppColors.blue)),
                                      TextSpan(text: rtl ? ' هذا الشهر' : ' this month'),
                                    ],
                                  )),
                                ],
                              ),
                            ),
                            const SizedBox(height: 16),
                            ResponsiveGrid(minItemWidth: 200, children: [
                              Kpi(icon: Icons.access_time, bg: AppColors.blueSoft, fg: AppColors.blue, label: rtl ? 'ساعات موفّرة' : 'Staff Hours Saved', value: rtl ? '٣٤' : '34', sub: rtl ? 'هذا الشهر' : 'This month'),
                              Kpi(icon: Icons.phone_callback_outlined, bg: AppColors.amberSoft, fg: AppColors.amber, label: rtl ? 'مكالمات بعد الدوام' : 'After-Hours Calls', value: rtl ? '١١٨' : '118', sub: rtl ? 'هذا الشهر' : 'This month'),
                              Kpi(icon: Icons.event_available, bg: AppColors.greenSoft, fg: AppColors.green, label: rtl ? 'المواعيد' : 'Bookings', value: rtl ? '٢٤٣' : '243', sub: rtl ? 'هذا الشهر' : 'This month'),
                            ]),
                            const SizedBox(height: 16),
                            AppCard(
                              padding: const EdgeInsets.all(22),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(rtl ? 'حجم المكالمات' : 'Call volume', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.ink)),
                                  const SizedBox(height: 14),
                                  LineChartView(data: vol),
                                ],
                              ),
                            ),
                            const SizedBox(height: 16),
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(16)),
                              child: Text(
                                rtl
                                    ? 'هذه معاينة مصغّرة. لوحة التاجر الكاملة (المحادثات، الخدمات، التقارير، الإعدادات) في تطبيق AtlasPrimeX.'
                                    : 'This is a compact preview. The full merchant dashboard (Conversations, Services, Reports, Settings) lives in the AtlasPrimeX app.',
                                textAlign: TextAlign.center,
                                style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w600, height: 1.5),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static String _grp(int n) {
    final s = n.toString();
    final b = StringBuffer();
    for (int i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) b.write(',');
      b.write(s[i]);
    }
    return b.toString();
  }

  static String _ar(String s) {
    final b = StringBuffer();
    for (final ch in s.split('')) {
      final c = ch.codeUnitAt(0);
      if (c >= 48 && c <= 57) {
        b.write(_arDigits[c - 48]);
      } else if (ch == ',') {
        b.write('٬');
      } else {
        b.write(ch);
      }
    }
    return b.toString();
  }
}

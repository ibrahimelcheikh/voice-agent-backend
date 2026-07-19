import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/merchant_repository.dart';
import '../data/models.dart';
import '../l10n/strings.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/charts.dart';
import '../widgets/ui.dart';

class ReportsScreen extends ConsumerWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(languageProvider);
    final s = S.of(lang);
    final rtl = lang == 'ar';
    final repo = ref.read(merchantRepositoryProvider);
    final openId = ref.watch(reportOpenProvider);

    if (openId != null) {
      Report? found;
      for (final group in repo.reports().values) {
        for (final r in group) {
          if (r.id == openId) found = r;
        }
      }
      if (found != null) return _ReportDetail(report: found, s: s, rtl: rtl, lang: lang);
    }

    final reports = repo.reports();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ScreenHeader(title: s.v('reportsTitle'), sub: s.v('reportsSub')),
        const SizedBox(height: 16),
        _group(ref, s, lang, Icons.phone_in_talk_outlined, AppColors.amberSoft, AppColors.amber,
            s.v('callAnalytics'), s.v('callAnalyticsSub'), reports['call']!),
        const SizedBox(height: 16),
        _group(ref, s, lang, Icons.trending_up, AppColors.greenSoft, AppColors.green,
            s.v('ordersRevenue'), s.v('ordersRevenueSub'), reports['orders']!),
      ],
    );
  }

  Widget _group(WidgetRef ref, S s, String lang, IconData icon, Color bg, Color fg, String title, String sub, List<Report> items) {
    return AppCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              IconBox(icon: icon, bg: bg, fg: fg),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 2),
                    Text(title, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900, color: AppColors.ink)),
                    const SizedBox(height: 4),
                    Text(sub, style: const TextStyle(color: AppColors.sub)),
                  ],
                ),
              ),
            ],
          ),
          for (int i = 0; i < items.length; i++)
            InkWell(
              onTap: () => ref.read(reportOpenProvider.notifier).state = items[i].id,
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 16),
                decoration: BoxDecoration(border: i == 0 ? null : const Border(top: BorderSide(color: AppColors.line))),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(child: Text(items[i].title(lang), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: AppColors.ink))),
                    const Icon(Icons.north_east, size: 20, color: AppColors.blue),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _ReportDetail extends ConsumerWidget {
  final Report report;
  final S s;
  final bool rtl;
  final String lang;
  const _ReportDetail({required this.report, required this.s, required this.rtl, required this.lang});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final repo = ref.read(merchantRepositoryProvider);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        BackLink(label: s.v('back'), rtl: rtl, onTap: () => ref.read(reportOpenProvider.notifier).state = null),
        const SizedBox(height: 16),
        Text(report.title(lang), style: const TextStyle(fontSize: 27, fontWeight: FontWeight.w900, letterSpacing: -0.5, color: AppColors.ink)),
        const SizedBox(height: 6),
        Text(report.desc(lang), style: const TextStyle(color: AppColors.sub)),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Align(
                alignment: AlignmentDirectional.centerStart,
                child: Pill(
                  bg: AppColors.cardAlt,
                  fg: AppColors.ink,
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.calendar_today_outlined, size: 14, color: AppColors.ink),
                    const SizedBox(width: 5),
                    Text(s.v('reportRange')),
                  ]),
                ),
              ),
              const SizedBox(height: 18),
              _chartFor(report.chart, repo.callVolume()),
            ],
          ),
        ),
        const SizedBox(height: 16),
        _statsFor(report),
      ],
    );
  }

  Widget _chartFor(String type, List<int> vol) {
    switch (type) {
      case 'bar':
        return BarChartView(
          data: const [22, 38, 54, 61, 48, 33, 26],
          labels: rtl ? const ['٩ص', '١١ص', '١م', '٣م', '٥م', '٧م', '٩م'] : const ['9a', '11a', '1p', '3p', '5p', '7p', '9p'],
        );
      case 'hbar':
        return const HBarChartView(rows: [
          MapEntry('HydraFacial', 84),
          MapEntry('Botox', 71),
          MapEntry('Laser', 58),
          MapEntry('Filler', 44),
          MapEntry('PRP', 22),
          MapEntry('Consult', 19),
        ]);
      case 'donut':
        return DonutChartView(
          segments: const [MapEntry(62, AppColors.green), MapEntry(26, AppColors.blue), MapEntry(12, AppColors.amber)],
          labels: rtl ? const ['إيجابي', 'محايد', 'قلق'] : const ['Positive', 'Neutral', 'Concerned'],
        );
      case 'line':
      default:
        return LineChartView(data: vol);
    }
  }

  Widget _statsFor(Report r) {
    final sets = <String, List<List<String>>>{
      'volume': [[s.v('totalCalls'), rtl ? '١٬٥٤٠' : '1,540'], [s.v('avgCalls'), rtl ? '٤٩٫٧' : '49.7']],
      'duration': [[rtl ? 'متوسط المدة' : 'Avg duration', rtl ? '١:١٢' : '1:12'], [rtl ? 'الأطول' : 'Longest', rtl ? '٤:٣٠' : '4:30']],
      'sentiment': [[rtl ? 'إيجابي' : 'Positive', '62%'], [rtl ? 'قلق' : 'Concerned', '12%']],
      'peak': [[rtl ? 'ساعة الذروة' : 'Peak hour', rtl ? '٣ م' : '3 PM'], [rtl ? 'الأهدأ' : 'Quietest', rtl ? '٩ م' : '9 PM']],
      'afterhours': [[rtl ? 'بعد العمل' : 'After-hours', rtl ? '١١٨' : '118'], [rtl ? 'نسبة الالتقاط' : 'Capture rate', '94%']],
      'bookvol': [[s.v('bookings'), rtl ? '٢٤٣' : '243'], [rtl ? 'معدل التحويل' : 'Conversion', '38%']],
      'revenue': [[rtl ? 'الإيراد' : 'Revenue', money(184500, lang)], [rtl ? 'متوسط الحجز' : 'Avg booking', money(760, lang)]],
      'bytreatment': [[rtl ? 'الأكثر حجزاً' : 'Top', 'HydraFacial'], [rtl ? 'الأعلى إيراداً' : 'Top revenue', 'Filler']],
      'channel': [[rtl ? 'صوت' : 'Voice', '62%'], [rtl ? 'واتساب' : 'WhatsApp', '26%']],
    };
    final stats = sets[r.id] ?? sets['volume']!;
    return Row(
      children: [
        for (int i = 0; i < stats.length; i++) ...[
          if (i > 0) const SizedBox(width: 14),
          Expanded(
            child: AppCard(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(stats[i][0], style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w700, fontSize: 14)),
                  const SizedBox(height: 8),
                  Text(stats[i][1], style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900, letterSpacing: -0.5, color: AppColors.ink)),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

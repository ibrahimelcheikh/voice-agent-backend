import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../theme/tokens.dart';

/// Area + line chart (matches the design's SVG line chart: dashed gridlines,
/// blue stroke with a soft gradient fill).
class LineChartView extends StatelessWidget {
  final List<int> data;
  final double height;
  const LineChartView({super.key, required this.data, this.height = 160});

  @override
  Widget build(BuildContext context) {
    final maxV = data.reduce((a, b) => a > b ? a : b).toDouble();
    final spots = <FlSpot>[
      for (int i = 0; i < data.length; i++) FlSpot(i.toDouble(), data[i].toDouble()),
    ];
    return SizedBox(
      height: height,
      child: LineChart(
        LineChartData(
          minX: 0,
          maxX: (data.length - 1).toDouble(),
          minY: 0,
          maxY: maxV * 1.08,
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: maxV / 3.7,
            getDrawingHorizontalLine: (_) => FlLine(
              color: AppColors.line,
              strokeWidth: 1,
              dashArray: [4, 4],
            ),
          ),
          titlesData: const FlTitlesData(show: false),
          borderData: FlBorderData(show: false),
          lineTouchData: const LineTouchData(enabled: false),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: false,
              color: AppColors.blue,
              barWidth: 2.5,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                gradient: const LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Color(0x4D2E6BFF), Color(0x002E6BFF)],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Vertical bar chart; the tallest bar is highlighted blue, the rest blueSoft.
class BarChartView extends StatelessWidget {
  final List<int> data;
  final List<String> labels;
  const BarChartView({super.key, required this.data, required this.labels});

  @override
  Widget build(BuildContext context) {
    final maxV = data.reduce((a, b) => a > b ? a : b);
    final maxIdx = data.indexOf(maxV);
    return SizedBox(
      height: 178,
      child: BarChart(
        BarChartData(
          alignment: BarChartAlignment.spaceAround,
          maxY: maxV * 1.05,
          barTouchData: BarTouchData(enabled: false),
          gridData: const FlGridData(show: false),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 24,
                getTitlesWidget: (value, meta) {
                  final i = value.toInt();
                  if (i < 0 || i >= labels.length) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(labels[i],
                        style: const TextStyle(color: AppColors.sub, fontSize: 12, fontWeight: FontWeight.w600)),
                  );
                },
              ),
            ),
          ),
          barGroups: [
            for (int i = 0; i < data.length; i++)
              BarChartGroupData(x: i, barRods: [
                BarChartRodData(
                  toY: data[i].toDouble(),
                  color: i == maxIdx ? AppColors.blue : AppColors.blueSoft,
                  width: 26,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(8),
                    topRight: Radius.circular(8),
                    bottomLeft: Radius.circular(3),
                    bottomRight: Radius.circular(3),
                  ),
                ),
              ]),
          ],
        ),
      ),
    );
  }
}

/// Horizontal breakdown bars (label + value above a rounded track). Rendered
/// faithfully to the design's progress-bar style.
class HBarChartView extends StatelessWidget {
  final List<MapEntry<String, int>> rows;
  const HBarChartView({super.key, required this.rows});

  static const _cols = [
    AppColors.blue,
    AppColors.green,
    AppColors.amber,
    AppColors.violet,
    AppColors.rose,
    AppColors.sub,
  ];

  @override
  Widget build(BuildContext context) {
    final maxV = rows.map((r) => r.value).reduce((a, b) => a > b ? a : b);
    return Column(
      children: [
        for (int i = 0; i < rows.length; i++) ...[
          if (i > 0) const SizedBox(height: 14),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(rows[i].key, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: AppColors.ink)),
                  Text('${rows[i].value}',
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14, color: AppColors.sub)),
                ],
              ),
              const SizedBox(height: 6),
              LayoutBuilder(builder: (context, c) {
                return Stack(children: [
                  Container(
                    height: 12,
                    decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(999)),
                  ),
                  Container(
                    height: 12,
                    width: c.maxWidth * rows[i].value / maxV,
                    decoration: BoxDecoration(color: _cols[i % _cols.length], borderRadius: BorderRadius.circular(999)),
                  ),
                ]);
              }),
            ],
          ),
        ],
      ],
    );
  }
}

/// Donut with the first segment's percentage in the center + a side legend.
class DonutChartView extends StatelessWidget {
  final List<MapEntry<int, Color>> segments; // pct -> color
  final List<String> labels;
  const DonutChartView({super.key, required this.segments, required this.labels});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      alignment: WrapAlignment.center,
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 24,
      runSpacing: 16,
      children: [
        SizedBox(
          width: 140,
          height: 140,
          child: Stack(
            alignment: Alignment.center,
            children: [
              PieChart(
                PieChartData(
                  startDegreeOffset: -90,
                  sectionsSpace: 0,
                  centerSpaceRadius: 40,
                  sections: [
                    for (final s in segments)
                      PieChartSectionData(
                        value: s.key.toDouble(),
                        color: s.value,
                        radius: 20,
                        showTitle: false,
                      ),
                  ],
                ),
              ),
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('${segments.first.key}%',
                      style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: AppColors.ink)),
                  Text(labels.first, style: const TextStyle(fontSize: 11, color: AppColors.sub)),
                ],
              ),
            ],
          ),
        ),
        Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (int i = 0; i < segments.length; i++)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 5),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 12,
                      height: 12,
                      decoration: BoxDecoration(color: segments[i].value, borderRadius: BorderRadius.circular(4)),
                    ),
                    const SizedBox(width: 10),
                    Text(labels[i], style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: AppColors.ink)),
                    const SizedBox(width: 10),
                    Text('${segments[i].key}%', style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w700, fontSize: 14)),
                  ],
                ),
              ),
          ],
        ),
      ],
    );
  }
}

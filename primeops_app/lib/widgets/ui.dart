import 'package:flutter/material.dart';
import '../theme/tokens.dart';

/// Console card — radius 20, soft double shadow.
class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;
  final BoxBorder? border;
  final Color? color;
  const AppCard({super.key, required this.child, this.padding, this.onTap, this.border, this.color});

  @override
  Widget build(BuildContext context) {
    final content = Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: color ?? AppColors.card,
        borderRadius: BorderRadius.circular(20),
        boxShadow: (color == AppColors.cardAlt) ? null : kCardShadow,
        border: border,
      ),
      child: child,
    );
    if (onTap == null) return content;
    return InkWell(onTap: onTap, borderRadius: BorderRadius.circular(20), child: content);
  }
}

class Pill extends StatelessWidget {
  final Widget child;
  final Color bg;
  final Color fg;
  final double fontSize;
  final EdgeInsets padding;
  const Pill({
    super.key,
    required this.child,
    required this.bg,
    required this.fg,
    this.fontSize = 12,
    this.padding = const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
      child: DefaultTextStyle.merge(
        style: TextStyle(color: fg, fontSize: fontSize, fontWeight: FontWeight.w700),
        child: IconTheme.merge(data: IconThemeData(color: fg, size: fontSize + 2), child: child),
      ),
    );
  }
}

class IconBox extends StatelessWidget {
  final IconData icon;
  final Color bg;
  final Color fg;
  final double size;
  final double iconSize;
  const IconBox({super.key, required this.icon, required this.bg, required this.fg, this.size = 44, this.iconSize = 20});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(13)),
      child: Icon(icon, color: fg, size: iconSize),
    );
  }
}

/// Section header (title 27/900 + optional sub, optional right widget).
class Head extends StatelessWidget {
  final String title;
  final String? sub;
  final Widget? right;
  const Head({super.key, required this.title, this.sub, this.right});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontSize: 27, fontWeight: FontWeight.w900, letterSpacing: -0.5, color: AppColors.ink)),
                if (sub != null) ...[
                  const SizedBox(height: 6),
                  Text(sub!, style: const TextStyle(color: AppColors.sub, height: 1.45)),
                ],
              ],
            ),
          ),
          if (right != null) right!,
        ],
      ),
    );
  }
}

class Kpi extends StatelessWidget {
  final IconData icon;
  final Color bg;
  final Color fg;
  final String label;
  final String value;
  final String sub;
  const Kpi({super.key, required this.icon, required this.bg, required this.fg, required this.label, required this.value, required this.sub});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: Text(label, style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w700, fontSize: 14))),
              IconBox(icon: icon, bg: bg, fg: fg, size: 40),
            ],
          ),
          const SizedBox(height: 14),
          Text(value, style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w900, letterSpacing: -0.8, height: 1, color: AppColors.ink)),
          const SizedBox(height: 6),
          Text(sub, style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w600, fontSize: 13.5)),
        ],
      ),
    );
  }
}

/// Responsive auto-fill grid (design's grid(min,gap)).
class ResponsiveGrid extends StatelessWidget {
  final double minItemWidth;
  final double gap;
  final List<Widget> children;
  const ResponsiveGrid({super.key, required this.minItemWidth, this.gap = 16, required this.children});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, c) {
      final w = c.maxWidth;
      int cols = (w / minItemWidth).floor();
      if (cols < 1) cols = 1;
      final itemW = (w - gap * (cols - 1)) / cols;
      return Wrap(
        spacing: gap,
        runSpacing: gap,
        children: [
          for (final child in children) SizedBox(width: itemW, child: child),
        ],
      );
    });
  }
}

class PillButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final VoidCallback? onTap;
  final Color bg;
  final Color fg;
  final BoxBorder? border;
  final bool fullWidth;
  const PillButton({super.key, required this.label, this.icon, this.onTap, required this.bg, required this.fg, this.border, this.fullWidth = false});

  factory PillButton.primary(String label, {IconData? icon, VoidCallback? onTap, bool fullWidth = false, Color? bg}) =>
      PillButton(label: label, icon: icon, onTap: onTap, bg: bg ?? AppColors.blue, fg: Colors.white, fullWidth: fullWidth);
  factory PillButton.ghost(String label, {IconData? icon, VoidCallback? onTap, bool fullWidth = false}) =>
      PillButton(label: label, icon: icon, onTap: onTap, bg: AppColors.card, fg: AppColors.ink, border: Border.all(color: AppColors.line, width: 1.5), fullWidth: fullWidth);

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap ?? () {},
        borderRadius: BorderRadius.circular(999),
        child: Container(
          width: fullWidth ? double.infinity : null,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 11),
          decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999), border: border),
          child: Row(
            mainAxisSize: fullWidth ? MainAxisSize.max : MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (icon != null) ...[Icon(icon, size: 18, color: fg), const SizedBox(width: 7)],
              Flexible(child: Text(label, overflow: TextOverflow.ellipsis, style: TextStyle(color: fg, fontWeight: FontWeight.w800, fontSize: 14.5))),
            ],
          ),
        ),
      ),
    );
  }
}

class AppToggle extends StatelessWidget {
  final bool on;
  final ValueChanged<bool>? onChanged;
  const AppToggle({super.key, required this.on, this.onChanged});
  @override
  Widget build(BuildContext context) {
    final track = Container(
      width: 46,
      height: 27,
      decoration: BoxDecoration(color: on ? AppColors.blue : AppColors.toggleOff, borderRadius: BorderRadius.circular(999)),
      child: Stack(children: [
        AnimatedPositioned(
          duration: const Duration(milliseconds: 160),
          top: 3,
          left: on ? 22 : 3,
          child: Container(
            width: 21,
            height: 21,
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(999), boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 3, offset: Offset(0, 1))]),
          ),
        ),
      ]),
    );
    if (onChanged == null) return track;
    return GestureDetector(onTap: () => onChanged!(!on), child: track);
  }
}

class BackLink extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  const BackLink({super.key, required this.label, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: AlignmentDirectional.centerStart,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.arrow_back, size: 18, color: AppColors.sub),
            const SizedBox(width: 6),
            Text(label, style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w800, fontSize: 15)),
          ]),
        ),
      ),
    );
  }
}

/// Small "mini" stat used on merchant cards.
class MiniStat extends StatelessWidget {
  final String label;
  final String value;
  const MiniStat({super.key, required this.label, required this.value});
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(color: AppColors.cardAlt, borderRadius: BorderRadius.circular(11)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: AppColors.sub, fontSize: 11, fontWeight: FontWeight.w700)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14, color: AppColors.ink)),
        ],
      ),
    );
  }
}

const sectionH = TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.ink);

/// Renders a "start → end" time range with a real arrow icon (fonts lack U+2192).
Widget hoursRow(String text, {Color? color, double size = 13}) {
  final parts = text.split('→');
  final style = TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: size);
  if (parts.length < 2) return Text(text, style: style);
  return Row(mainAxisSize: MainAxisSize.min, children: [
    Text(parts[0].trim(), style: style),
    Padding(padding: const EdgeInsets.symmetric(horizontal: 5), child: Icon(Icons.arrow_forward, size: size, color: color)),
    Text(parts[1].trim(), style: style),
  ]);
}

/// Group an integer with thousands commas (e.g. 6180 -> "6,180").
String fmtInt(int n) {
  final s = n.toString();
  final b = StringBuffer();
  for (int i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) b.write(',');
    b.write(s[i]);
  }
  return b.toString();
}

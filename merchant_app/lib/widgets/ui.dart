import 'package:flutter/material.dart';
import '../theme/tokens.dart';

/// Rounded card with the design's soft double shadow. radius 24 by default.
class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final double radius;
  final Color? color;
  final BoxBorder? border;
  final VoidCallback? onTap;
  const AppCard({
    super.key,
    required this.child,
    this.padding,
    this.radius = 24,
    this.color,
    this.border,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final content = Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: color ?? AppColors.card,
        borderRadius: BorderRadius.circular(radius),
        boxShadow: color == AppColors.cardAlt ? null : kCardShadow,
        border: border,
      ),
      child: child,
    );
    if (onTap == null) return content;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(radius),
      child: content,
    );
  }
}

/// Rounded label chip.
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
    this.fontSize = 12.5,
    this.padding = const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
      child: DefaultTextStyle.merge(
        style: TextStyle(color: fg, fontSize: fontSize, fontWeight: FontWeight.w700),
        child: IconTheme.merge(
          data: IconThemeData(color: fg, size: fontSize + 2),
          child: child,
        ),
      ),
    );
  }
}

/// Rounded coloured square holding an icon (46x46 default).
class IconBox extends StatelessWidget {
  final IconData icon;
  final Color bg;
  final Color fg;
  final double size;
  final double iconSize;
  const IconBox({
    super.key,
    required this.icon,
    required this.bg,
    required this.fg,
    this.size = 46,
    this.iconSize = 22,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(14)),
      child: Icon(icon, color: fg, size: iconSize),
    );
  }
}

/// The design's pill toggle (48x28). Purely visual unless [onChanged] given.
class AppToggle extends StatelessWidget {
  final bool on;
  final ValueChanged<bool>? onChanged;
  const AppToggle({super.key, required this.on, this.onChanged});

  @override
  Widget build(BuildContext context) {
    final track = Container(
      width: 48,
      height: 28,
      decoration: BoxDecoration(
        color: on ? AppColors.blue : AppColors.toggleOff,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Stack(
        children: [
          AnimatedPositioned(
            duration: const Duration(milliseconds: 180),
            top: 3,
            left: on ? 23 : 3,
            child: Container(
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(999),
                boxShadow: const [
                  BoxShadow(color: Color(0x33000000), blurRadius: 3, offset: Offset(0, 1)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
    if (onChanged == null) return track;
    return GestureDetector(onTap: () => onChanged!(!on), child: track);
  }
}

/// Big title + subtitle header used at the top of most screens.
class ScreenHeader extends StatelessWidget {
  final String title;
  final String? sub;
  final bool noTop;
  const ScreenHeader({super.key, required this.title, this.sub, this.noTop = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(4, noTop ? 4 : 8, 4, noTop ? 4 : 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                  fontSize: 28, fontWeight: FontWeight.w900, letterSpacing: -0.5, color: AppColors.ink)),
          if (sub != null) ...[
            const SizedBox(height: 6),
            Text(sub!, style: const TextStyle(color: AppColors.sub, height: 1.45)),
          ],
        ],
      ),
    );
  }
}

/// KPI stat card (label + big value + sub).
class KpiCard extends StatelessWidget {
  final IconData icon;
  final Color bg;
  final Color fg;
  final String label;
  final String value;
  final String sub;
  const KpiCard({
    super.key,
    required this.icon,
    required this.bg,
    required this.fg,
    required this.label,
    required this.value,
    required this.sub,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(label,
                    style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w700, fontSize: 15)),
              ),
              IconBox(icon: icon, bg: bg, fg: fg),
            ],
          ),
          const SizedBox(height: 18),
          Text(value,
              style: const TextStyle(
                  fontSize: 40, fontWeight: FontWeight.w900, letterSpacing: -1, height: 1, color: AppColors.ink)),
          const SizedBox(height: 8),
          Text(sub, style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

/// Pill buttons matching the design (primary blue, ghost, dark).
class PillButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final VoidCallback? onTap;
  final Color bg;
  final Color fg;
  final BoxBorder? border;
  final bool fullWidth;
  final EdgeInsets padding;
  final List<BoxShadow>? shadow;
  const PillButton({
    super.key,
    required this.label,
    this.icon,
    this.onTap,
    required this.bg,
    required this.fg,
    this.border,
    this.fullWidth = false,
    this.padding = const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
    this.shadow,
  });

  factory PillButton.primary(String label, {IconData? icon, VoidCallback? onTap, bool fullWidth = false}) =>
      PillButton(label: label, icon: icon, onTap: onTap, bg: AppColors.blue, fg: Colors.white, fullWidth: fullWidth);

  factory PillButton.ghost(String label, {IconData? icon, VoidCallback? onTap, bool fullWidth = false}) => PillButton(
        label: label,
        icon: icon,
        onTap: onTap,
        bg: AppColors.card,
        fg: AppColors.ink,
        border: Border.all(color: AppColors.line, width: 1.5),
        fullWidth: fullWidth,
      );

  factory PillButton.dark(String label, {IconData? icon, VoidCallback? onTap, bool fullWidth = false}) =>
      PillButton(label: label, icon: icon, onTap: onTap, bg: AppColors.ink, fg: Colors.white, fullWidth: fullWidth);

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap ?? () {},
        borderRadius: BorderRadius.circular(999),
        child: Container(
          width: fullWidth ? double.infinity : null,
          padding: padding,
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(999),
            border: border,
            boxShadow: shadow,
          ),
          child: Row(
            mainAxisSize: fullWidth ? MainAxisSize.max : MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (icon != null) ...[Icon(icon, size: 18, color: fg), const SizedBox(width: 8)],
              Flexible(
                child: Text(label,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(color: fg, fontWeight: FontWeight.w800, fontSize: 15)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// A static slider track with a knob at [pct] percent (voice speed / ambience).
class StaticSlider extends StatelessWidget {
  final double pct;
  const StaticSlider({super.key, required this.pct});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, c) {
      final w = c.maxWidth;
      return SizedBox(
        height: 20,
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            Positioned(
              top: 7,
              left: 0,
              right: 0,
              child: Container(height: 6, decoration: BoxDecoration(color: AppColors.line, borderRadius: BorderRadius.circular(999))),
            ),
            Positioned(
              top: 7,
              left: 0,
              child: Container(
                height: 6,
                width: w * pct / 100,
                decoration: BoxDecoration(color: AppColors.ink, borderRadius: BorderRadius.circular(999)),
              ),
            ),
            Positioned(
              top: 0,
              left: (w * pct / 100) - 10,
              child: Container(
                width: 20,
                height: 20,
                decoration: BoxDecoration(
                  color: AppColors.ink,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 3),
                  boxShadow: const [BoxShadow(color: Color(0x40000000), blurRadius: 4, offset: Offset(0, 1))],
                ),
              ),
            ),
          ],
        ),
      );
    });
  }
}

/// Voice option row (Reem / Marissa) with a play affordance.
class VoiceRow extends StatelessWidget {
  final String name;
  final String desc;
  final bool active;
  const VoiceRow({super.key, required this.name, required this.desc, required this.active});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: active ? AppColors.blueSoft : AppColors.cardAlt,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: active ? AppColors.blue : Colors.transparent, width: 1.5),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: const BoxDecoration(
              gradient: LinearGradient(colors: [AppColors.blue, AppColors.blueDeep], begin: Alignment.topLeft, end: Alignment.bottomRight),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Text(name.characters.first, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: AppColors.ink)),
                Text(desc, style: const TextStyle(color: AppColors.sub, fontSize: 13.5)),
              ],
            ),
          ),
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: active ? AppColors.blue : AppColors.sub, width: 2),
            ),
            child: Icon(Icons.play_arrow, size: 18, color: active ? AppColors.blue : AppColors.sub),
          ),
        ],
      ),
    );
  }
}

/// Back button used on detail screens.
class BackLink extends StatelessWidget {
  final String label;
  final bool rtl;
  final VoidCallback onTap;
  const BackLink({super.key, required this.label, required this.rtl, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: AlignmentDirectional.centerStart,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(rtl ? Icons.chevron_right : Icons.arrow_back, size: 18, color: AppColors.sub),
              const SizedBox(width: 6),
              Text(label, style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w800, fontSize: 15)),
            ],
          ),
        ),
      ),
    );
  }
}

/// Renders a "start → end" time range with a real arrow icon (the fonts lack
/// U+2192). Kept LTR so the time reads the same in EN and AR, as in the design.
Widget hoursRow(String text, {Color? color, double size = 14}) {
  final parts = text.split('→');
  final style = TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: size);
  if (parts.length < 2) return Text(text, style: style);
  return Directionality(
    textDirection: TextDirection.ltr,
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(parts[0].trim(), style: style),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 5),
          child: Icon(Icons.arrow_forward, size: size, color: color),
        ),
        Text(parts[1].trim(), style: style),
      ],
    ),
  );
}

/// Small section title (fontWeight 900, 21px) used in Settings.
class SectionTitle extends StatelessWidget {
  final String text;
  const SectionTitle(this.text, {super.key});
  @override
  Widget build(BuildContext context) =>
      Text(text, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 21, color: AppColors.ink));
}

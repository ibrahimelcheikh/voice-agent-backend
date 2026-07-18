import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/mock_data.dart';
import '../data/models.dart';

/// UI language: 'en' or 'ar'. Drives Directionality + font family app-wide.
final languageProvider = StateProvider<String>((ref) => 'en');

/// Currently selected branch (multi-branch switcher in the top bar).
final branchProvider = StateProvider<Branch>((ref) => kBranches.first);

/// Active section in the drawer nav.
final navProvider = StateProvider<String>((ref) => 'overview');

/// Active tab inside the Settings screen.
final settingsTabProvider = StateProvider<String>((ref) => 'general');

/// Open service detail (service id) — null shows the list.
final serviceOpenProvider = StateProvider<String?>((ref) => null);

/// Open report detail (report id) — null shows the report list.
final reportOpenProvider = StateProvider<String?>((ref) => null);

/// Expanded FAQ index in Settings ▸ FAQ (design defaults the first open).
final openFaqProvider = StateProvider<int>((ref) => 0);

/// Navigate to a section and reset any open detail views (mirrors go() in the
/// design).
void goTo(WidgetRef ref, String key) {
  ref.read(navProvider.notifier).state = key;
  ref.read(serviceOpenProvider.notifier).state = null;
  ref.read(reportOpenProvider.notifier).state = null;
}

/// Currency formatter matching the design's `money()` helper.
String money(int n, String lang) {
  final s = _groupThousands(n);
  if (lang == 'ar') {
    return '${_toArabicDigits(s)} ريال';
  }
  return 'SAR $s';
}

String _groupThousands(int n) {
  final str = n.toString();
  final buf = StringBuffer();
  for (int i = 0; i < str.length; i++) {
    if (i > 0 && (str.length - i) % 3 == 0) buf.write(',');
    buf.write(str[i]);
  }
  return buf.toString();
}

const _arabicDigits = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];

String _toArabicDigits(String s) {
  final buf = StringBuffer();
  for (final ch in s.split('')) {
    final code = ch.codeUnitAt(0);
    if (code >= 48 && code <= 57) {
      buf.write(_arabicDigits[code - 48]);
    } else if (ch == ',') {
      buf.write('٬'); // arabic thousands separator
    } else {
      buf.write(ch);
    }
  }
  return buf.toString();
}

/// Resolve a localized `{en, ar}` map for the current language.
String tr(LMap m, String lang) => loc(m, lang);

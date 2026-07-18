import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'data/mock_data.dart';
import 'data/merchant_repository.dart';
import 'state/app_state.dart';
import 'theme/tokens.dart';
import 'screens/shell.dart';
import 'screens/auth_gate.dart';

void main() {
  // Optional deep-linking via query params, e.g.
  // ?lang=ar&nav=settings&tab=voice  or  ?nav=services&service=botox
  final q = Uri.base.queryParameters;
  final overrides = <Override>[];
  if (q['lang'] == 'ar' || q['lang'] == 'en') {
    overrides.add(languageProvider.overrideWith((ref) => q['lang']!));
  }
  if (q['nav'] != null) overrides.add(navProvider.overrideWith((ref) => q['nav']!));
  if (q['tab'] != null) overrides.add(settingsTabProvider.overrideWith((ref) => q['tab']!));
  if (q['service'] != null) overrides.add(serviceOpenProvider.overrideWith((ref) => q['service']));
  if (q['report'] != null) overrides.add(reportOpenProvider.overrideWith((ref) => q['report']));
  if (q['branch'] != null) {
    final b = kBranches.where((x) => '${x.id}' == q['branch']);
    if (b.isNotEmpty) overrides.add(branchProvider.overrideWith((ref) => b.first));
  }
  runApp(ProviderScope(overrides: overrides, child: const MerchantApp()));
}

class MerchantApp extends ConsumerWidget {
  const MerchantApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(languageProvider);
    final rtl = lang == 'ar';

    // Poppins for English, Noto Sans Arabic for Arabic (the design's font choice).
    // Self-hosted as bundled assets so there is no runtime CDN dependency —
    // reliable offline, in production, and for CanvasKit text shaping.
    final family = rtl ? 'NotoSansArabic' : 'Poppins';
    // Fallback covers mixed-script strings (the "ع" language toggle in EN, and
    // Latin/numerals like "SAR"/"Cal.com" in AR).
    final fallback = rtl ? const ['Poppins'] : const ['NotoSansArabic'];
    final base = ThemeData(
      useMaterial3: true,
      fontFamily: family,
      fontFamilyFallback: fallback,
      scaffoldBackgroundColor: AppColors.bg,
      colorScheme: ColorScheme.fromSeed(seedColor: AppColors.blue, primary: AppColors.blue),
    );

    final theme = base.copyWith(
      textTheme: base.textTheme.apply(bodyColor: AppColors.ink, displayColor: AppColors.ink),
      splashFactory: NoSplash.splashFactory,
      highlightColor: Colors.transparent,
    );

    return MaterialApp(
      title: 'AtlasPrimeX — Merchant',
      debugShowCheckedModeBanner: false,
      theme: theme,
      locale: Locale(lang),
      supportedLocales: const [Locale('en'), Locale('ar')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder: (context, child) => Directionality(
        textDirection: rtl ? TextDirection.rtl : TextDirection.ltr,
        child: child!,
      ),
      home: kUseMockData ? const MerchantShell() : const AuthGate(),
    );
  }
}

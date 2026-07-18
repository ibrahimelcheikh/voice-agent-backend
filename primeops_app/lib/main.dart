import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'data/mock_data.dart';
import 'state/app_state.dart';
import 'theme/tokens.dart';
import 'screens/shell.dart';

void main() {
  // Optional deep-linking for testing/sharing, e.g.
  //   ?nav=merchants&merchant=1   ?view=merchant&mvlang=ar   ?nav=onboarding&step=3
  final q = Uri.base.queryParameters;
  final overrides = <Override>[];
  if (q['nav'] != null) overrides.add(navProvider.overrideWith((ref) => q['nav']!));
  if (q['view'] == 'merchant') overrides.add(merchantViewProvider.overrideWith((ref) => true));
  if (q['mvlang'] == 'ar' || q['mvlang'] == 'en') {
    overrides.add(merchantViewLangProvider.overrideWith((ref) => q['mvlang']!));
  }
  if (q['merchant'] != null) {
    final m = kMerchants.where((x) => '${x.id}' == q['merchant']);
    if (m.isNotEmpty) {
      overrides.add(activeMerchantProvider.overrideWith((ref) => m.first));
      overrides.add(navProvider.overrideWith((ref) => 'merchants'));
    }
  }
  if (q['step'] != null) {
    final s = int.tryParse(q['step']!);
    if (s != null) overrides.add(onboardingStepProvider.overrideWith((ref) => s));
  }
  if (q['adduser'] == '1') overrides.add(addUserProvider.overrideWith((ref) => true));
  runApp(ProviderScope(overrides: overrides, child: const PrimeOpsApp()));
}

class PrimeOpsApp extends StatelessWidget {
  const PrimeOpsApp({super.key});

  @override
  Widget build(BuildContext context) {
    final base = ThemeData(
      useMaterial3: true,
      fontFamily: 'Poppins',
      fontFamilyFallback: const ['NotoSansArabic'],
      scaffoldBackgroundColor: AppColors.bg,
      colorScheme: ColorScheme.fromSeed(seedColor: AppColors.blue, primary: AppColors.blue),
    );
    return MaterialApp(
      title: 'AtlasPrimeX — PrimeOps',
      debugShowCheckedModeBanner: false,
      theme: base.copyWith(
        textTheme: base.textTheme.apply(bodyColor: AppColors.ink, displayColor: AppColors.ink),
        splashFactory: NoSplash.splashFactory,
        highlightColor: Colors.transparent,
      ),
      supportedLocales: const [Locale('en'), Locale('ar')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      home: const OpsShell(),
    );
  }
}

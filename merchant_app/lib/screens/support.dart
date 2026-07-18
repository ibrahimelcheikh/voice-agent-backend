import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../l10n/strings.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class SupportScreen extends ConsumerWidget {
  const SupportScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(languageProvider);
    final s = S.of(lang);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 8),
        Text(s.nav('support'), style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900, color: AppColors.ink)),
        const SizedBox(height: 16),
        AppCard(
          padding: const EdgeInsets.all(26),
          child: Column(
            children: [
              const IconBox(icon: Icons.chat_bubble_outline, bg: AppColors.blueSoft, fg: AppColors.blue),
              const SizedBox(height: 12),
              const Text('AtlasPrimeX Support', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 20, color: AppColors.ink)),
              const SizedBox(height: 6),
              const Text('support@atlasprimex.ai', style: TextStyle(color: AppColors.sub)),
              const SizedBox(height: 16),
              PillButton.dark(s.v('startChat'), icon: Icons.chat_bubble_outline),
            ],
          ),
        ),
      ],
    );
  }
}

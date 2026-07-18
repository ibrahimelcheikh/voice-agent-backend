import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models.dart';
import '../theme/tokens.dart';

// ---- navigation / view state ----
final navProvider = StateProvider<String>((ref) => 'overview');
final merchantViewProvider = StateProvider<bool>((ref) => false);
final activeMerchantProvider = StateProvider<Merchant?>((ref) => null);

// ---- section-local state ----
final onboardingStepProvider = StateProvider<int>((ref) => 0);
final promptSelProvider = StateProvider<int>((ref) => 1); // merchant id
final alertFilterProvider = StateProvider<String>((ref) => 'all');
final ticketFilterProvider = StateProvider<String>((ref) => 'all');
final addUserProvider = StateProvider<bool>((ref) => false);
final merchantViewLangProvider = StateProvider<String>((ref) => 'en');

/// go(k) in the design: switch section + clear the open merchant detail.
void goTo(WidgetRef ref, String key) {
  ref.read(navProvider.notifier).state = key;
  ref.read(activeMerchantProvider.notifier).state = null;
}

// ---- design status maps ----
class Badge {
  final String label;
  final Color bg;
  final Color fg;
  const Badge(this.label, this.bg, this.fg);
}

Badge statusPill(String s) => const {
      'live': Badge('Live', AppColors.greenSoft, AppColors.green),
      'onboarding': Badge('Onboarding', AppColors.blueSoft, AppColors.blue),
      'paused': Badge('Paused', AppColors.roseSoft, AppColors.rose),
    }[s]!;

class Sev {
  final Color bg;
  final Color fg;
  final IconData icon;
  final String label;
  const Sev(this.bg, this.fg, this.icon, this.label);
}

Sev sevMap(String s) => {
      'critical': const Sev(AppColors.roseSoft, AppColors.rose, Icons.warning_amber_rounded, 'Critical'),
      'warning': const Sev(AppColors.amberSoft, AppColors.amber, Icons.warning_amber_rounded, 'Warning'),
      'info': const Sev(AppColors.blueSoft, AppColors.blue, Icons.bolt, 'Info'),
    }[s]!;

Badge ticketStatus(String s) => const {
      'open': Badge('Open', AppColors.amberSoft, AppColors.amber),
      'in_progress': Badge('In progress', AppColors.blueSoft, AppColors.blue),
      'resolved': Badge('Resolved', AppColors.greenSoft, AppColors.green),
    }[s]!;

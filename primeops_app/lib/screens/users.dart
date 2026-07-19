import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models.dart';
import '../data/ops_repository.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class UsersScreen extends ConsumerWidget {
  const UsersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final desktop = MediaQuery.of(context).size.width >= 900;
    final adding = ref.watch(addUserProvider);
    final users = ref.read(opsRepositoryProvider).users();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Head(
          title: 'Users',
          sub: 'Your internal team and their access.',
          right: PillButton.primary('Add user', icon: Icons.add, onTap: () => ref.read(addUserProvider.notifier).state = !adding),
        ),
        if (adding) ...[
          AppCard(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Invite a team member', style: sectionH),
                const SizedBox(height: 14),
                ResponsiveGrid(minItemWidth: desktop ? 240 : 200, children: [
                  _input('Full name'),
                  _input('Email'),
                  _roleSelect(),
                ]),
                const SizedBox(height: 14),
                Row(children: [
                  PillButton.ghost('Cancel', onTap: () => ref.read(addUserProvider.notifier).state = false),
                  const SizedBox(width: 10),
                  PillButton.primary('Send invite', onTap: () => ref.read(addUserProvider.notifier).state = false),
                ]),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],
        for (final u in users) ...[
          _userCard(u),
          const SizedBox(height: 16),
        ],
      ],
    );
  }

  Color _roleColor(String r) => r == 'Owner' ? AppColors.violet : r.contains('Lead') ? AppColors.blue : AppColors.sub;

  Widget _userCard(OpsUser u) {
    final initials = u.name.split(' ').map((x) => x[0]).take(2).join();
    return AppCard(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Row(children: [
        Container(
          width: 44, height: 44,
          decoration: const BoxDecoration(gradient: LinearGradient(colors: [AppColors.blue, AppColors.blueDeep]), shape: BoxShape.circle),
          alignment: Alignment.center,
          child: Text(initials, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16)),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(u.name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15.5, color: AppColors.ink)),
              Text(u.email, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: AppColors.sub, fontSize: 13)),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Pill(bg: AppColors.cardAlt, fg: _roleColor(u.role), child: Text(u.role)),
        const SizedBox(width: 8),
        Pill(bg: u.active ? AppColors.greenSoft : AppColors.roseSoft, fg: u.active ? AppColors.green : AppColors.rose, child: Text(u.active ? 'Active' : 'Disabled')),
      ]),
    );
  }

  Widget _input(String hint) => TextField(
        style: const TextStyle(fontSize: 15, color: AppColors.ink),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: const TextStyle(color: AppColors.sub),
          filled: true,
          fillColor: AppColors.card,
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.line, width: 1.5)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.blue, width: 1.5)),
        ),
      );

  Widget _roleSelect() => Container(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: BoxDecoration(color: AppColors.card, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.line, width: 1.5)),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<String>(
            value: 'Support',
            isExpanded: true,
            icon: const Icon(Icons.keyboard_arrow_down, color: AppColors.sub),
            style: const TextStyle(fontSize: 15, color: AppColors.ink),
            padding: const EdgeInsets.symmetric(vertical: 11),
            items: const [
              DropdownMenuItem(value: 'Support', child: Text('Support')),
              DropdownMenuItem(value: 'Onboarding', child: Text('Onboarding')),
              DropdownMenuItem(value: 'Support Lead', child: Text('Support Lead')),
              DropdownMenuItem(value: 'Admin', child: Text('Admin')),
            ],
            onChanged: (_) {},
          ),
        ),
      );
}

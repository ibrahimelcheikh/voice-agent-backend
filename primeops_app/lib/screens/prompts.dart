import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models.dart';
import '../data/ops_repository.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class PromptsScreen extends ConsumerStatefulWidget {
  const PromptsScreen({super.key});
  @override
  ConsumerState<PromptsScreen> createState() => _PromptsScreenState();
}

class _PromptsScreenState extends ConsumerState<PromptsScreen> {
  final _ctl = TextEditingController();
  int? _lastId;

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  String _prompt(Merchant m) =>
      "You are the AI receptionist for ${m.name}, a ${m.type.toLowerCase()} in ${m.city}. "
      "Greet warmly and answer only from the clinic's real services, prices, and hours. "
      "Never invent prices or medical advice. Offer to book, confirm details, and send an SMS confirmation. "
      "If a caller is distressed or reports a complication, flag as urgent and transfer to a clinician.";

  @override
  Widget build(BuildContext context) {
    final desktop = MediaQuery.of(context).size.width >= 900;
    final merchants = ref.read(opsRepositoryProvider).merchants();
    final selId = ref.watch(promptSelProvider);
    final sel = merchants.firstWhere((m) => m.id == selId, orElse: () => merchants.first);
    if (_lastId != sel.id) {
      _lastId = sel.id;
      _ctl.text = _prompt(sel);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Head(title: 'Agent Config', sub: 'Tune the system prompt, voice, and guardrails per merchant.'),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(color: AppColors.card, borderRadius: BorderRadius.circular(14)),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<int>(
              value: sel.id,
              isExpanded: true,
              icon: const Icon(Icons.keyboard_arrow_down, color: AppColors.sub),
              borderRadius: BorderRadius.circular(14),
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: AppColors.ink),
              padding: const EdgeInsets.symmetric(vertical: 14),
              items: [for (final m in merchants) DropdownMenuItem(value: m.id, child: Text('${m.name} — ${m.city}'))],
              onChanged: (v) {
                if (v != null) ref.read(promptSelProvider.notifier).state = v;
              },
            ),
          ),
        ),
        const SizedBox(height: 18),
        AppCard(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('System prompt', style: sectionH),
              const SizedBox(height: 8),
              const Text('The core instructions. Business facts stay grounded — the agent never invents prices or availability.', style: TextStyle(color: AppColors.sub)),
              const SizedBox(height: 12),
              TextField(
                controller: _ctl,
                maxLines: 7,
                style: const TextStyle(fontSize: 14.5, color: AppColors.ink, height: 1.6),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: AppColors.card,
                  contentPadding: const EdgeInsets.all(14),
                  enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.line, width: 1.5)),
                  focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.blue, width: 1.5)),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        ResponsiveGrid(minItemWidth: desktop ? 330 : 260, children: [
          AppCard(
            padding: const EdgeInsets.all(22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Voice', style: sectionH),
                const SizedBox(height: 14),
                _voiceRow('Reem', 'Arabic · Khaleeji', sel.langs.contains('ar')),
                const SizedBox(height: 10),
                _voiceRow('Marissa', 'Female · English', !sel.langs.contains('ar')),
              ],
            ),
          ),
          AppCard(
            padding: const EdgeInsets.all(22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Guardrails', style: sectionH),
                const SizedBox(height: 8),
                for (int i = 0; i < 4; i++)
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: BoxDecoration(border: i == 0 ? null : const Border(top: BorderSide(color: AppColors.line))),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(child: Text(['Never quote unlisted prices', 'Escalate medical complications', 'Confirm before booking', 'Refuse off-topic requests'][i], style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5, color: AppColors.ink))),
                        const SizedBox(width: 10),
                        const AppToggle(on: true),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ]),
        const SizedBox(height: 18),
        PillButton.primary('Save config', icon: Icons.check),
      ],
    );
  }

  Widget _voiceRow(String name, String desc, bool active) {
    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: active ? AppColors.blueSoft : AppColors.cardAlt,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: active ? AppColors.blue : Colors.transparent, width: 1.5),
      ),
      child: Row(children: [
        Container(
          width: 40, height: 40,
          decoration: const BoxDecoration(gradient: LinearGradient(colors: [AppColors.blue, AppColors.blueDeep]), shape: BoxShape.circle),
          alignment: Alignment.center,
          child: Text(name[0], style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
        ),
        const SizedBox(width: 13),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.ink)),
              Text(desc, style: const TextStyle(color: AppColors.sub, fontSize: 13)),
            ],
          ),
        ),
        if (active) const Icon(Icons.check_circle, size: 20, color: AppColors.blue),
      ]),
    );
  }
}

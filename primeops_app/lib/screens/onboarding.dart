import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

const _steps = ['Business', 'Channels', 'Hours', 'Services', 'Review'];

class OnboardingScreen extends ConsumerWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final desktop = MediaQuery.of(context).size.width >= 900;
    final step = ref.watch(onboardingStepProvider);
    final setStep = ref.read(onboardingStepProvider.notifier);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Head(title: 'Onboard a merchant', sub: "Spin up a new client's AI agent in a few steps."),
        // stepper
        Row(
          children: [
            for (int i = 0; i < _steps.length; i++)
              Expanded(
                flex: desktop ? 1 : 0,
                child: Row(
                  mainAxisSize: desktop ? MainAxisSize.max : MainAxisSize.min,
                  children: [
                    Container(
                      width: 30, height: 30,
                      decoration: BoxDecoration(color: i <= step ? AppColors.blue : AppColors.cardAlt, shape: BoxShape.circle),
                      alignment: Alignment.center,
                      child: i < step
                          ? const Icon(Icons.check, size: 16, color: Colors.white)
                          : Text('${i + 1}', style: TextStyle(color: i <= step ? Colors.white : AppColors.sub, fontWeight: FontWeight.w800, fontSize: 14)),
                    ),
                    const SizedBox(width: 8),
                    Text(_steps[i], style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5, color: i == step ? AppColors.ink : AppColors.sub)),
                    if (desktop && i < _steps.length - 1) ...[
                      const SizedBox(width: 8),
                      Expanded(child: Container(height: 2, color: i < step ? AppColors.blue : AppColors.line)),
                      const SizedBox(width: 8),
                    ] else if (i < _steps.length - 1)
                      const SizedBox(width: 14),
                  ],
                ),
              ),
          ],
        ),
        const SizedBox(height: 20),
        AppCard(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (step == 0) ..._business(),
              if (step == 1) ..._channels(),
              if (step == 2) ..._hours(),
              if (step == 3) ..._services(),
              if (step == 4) ..._review(),
              const SizedBox(height: 22),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Opacity(
                    opacity: step == 0 ? 0.4 : 1,
                    child: PillButton.ghost('Back', icon: Icons.chevron_left, onTap: step == 0 ? () {} : () => setStep.state = step - 1),
                  ),
                  if (step < _steps.length - 1)
                    _continueBtn(() => setStep.state = step + 1)
                  else
                    PillButton.primary('Launch agent', icon: Icons.bolt, bg: AppColors.green),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _continueBtn(VoidCallback onTap) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(999),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 11),
          decoration: BoxDecoration(color: AppColors.blue, borderRadius: BorderRadius.circular(999)),
          child: Row(mainAxisSize: MainAxisSize.min, children: const [
            Text('Continue', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14.5)),
            SizedBox(width: 6),
            Icon(Icons.chevron_right, size: 18, color: Colors.white),
          ]),
        ),
      );

  List<Widget> _business() => [
        const Text('Business details', style: sectionH),
        const SizedBox(height: 14),
        _field('Clinic name', 'e.g. Nova Skin Bar'),
        _field('City', 'e.g. Riyadh'),
        _field('Type', 'Med Spa / Dental / Clinic'),
        _field('Phone number', '+966 …'),
      ];

  List<Widget> _channels() => [
        const Text('Channels & language', style: sectionH),
        const SizedBox(height: 8),
        const Text('Pick where the agent answers and which languages it speaks.', style: TextStyle(color: AppColors.sub)),
        const SizedBox(height: 6),
        for (int i = 0; i < 4; i++)
          _toggleRow(['Voice calls', 'WhatsApp', 'Arabic (Khaleeji)', 'English'][i], i != 1, i == 0),
      ];

  List<Widget> _hours() => [
        const Text('Opening hours', style: sectionH),
        const SizedBox(height: 6),
        for (int i = 0; i < 6; i++)
          Container(
            padding: const EdgeInsets.symmetric(vertical: 11),
            decoration: BoxDecoration(border: i == 0 ? null : const Border(top: BorderSide(color: AppColors.line))),
            child: Row(children: [
              const AppToggle(on: true),
              const SizedBox(width: 14),
              SizedBox(width: 46, child: Text(['Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu'][i], style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink))),
              const Spacer(),
              Pill(bg: AppColors.cardAlt, fg: AppColors.ink, child: hoursRow('1:00 PM → 9:00 PM')),
            ]),
          ),
      ];

  List<Widget> _services() {
    const items = [['Botox', 'SAR 900+'], ['HydraFacial', 'SAR 650+'], ['Laser Hair Removal', 'SAR 400+']];
    return [
      const Text('Services & pricing', style: sectionH),
      const SizedBox(height: 8),
      const Text('Add the treatments the agent can quote and book.', style: TextStyle(color: AppColors.sub)),
      const SizedBox(height: 6),
      for (int i = 0; i < items.length; i++)
        Container(
          padding: const EdgeInsets.symmetric(vertical: 13),
          decoration: BoxDecoration(border: i == 0 ? null : const Border(top: BorderSide(color: AppColors.line))),
          child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text(items[i][0], style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.ink)),
            Text(items[i][1], style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.blue)),
          ]),
        ),
      const SizedBox(height: 14),
      PillButton.ghost('Add service', icon: Icons.add, fullWidth: true),
    ];
  }

  List<Widget> _review() {
    const rows = [
      ['Business', 'Nova Skin Bar · Riyadh'],
      ['Channels', 'Voice · Arabic'],
      ['Hours', 'Sat–Thu 1–9 PM'],
      ['Services', '3 added'],
      ['Voice', 'Reem (Khaleeji)'],
    ];
    return [
      const Text('Review & launch', style: sectionH),
      const SizedBox(height: 14),
      Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: AppColors.greenSoft, borderRadius: BorderRadius.circular(14)),
        child: Row(children: const [
          Icon(Icons.check_circle, size: 22, color: AppColors.green),
          SizedBox(width: 12),
          Expanded(child: Text('Everything looks ready. The agent will go live on save.', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.ink))),
        ]),
      ),
      const SizedBox(height: 14),
      for (int i = 0; i < rows.length; i++)
        Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(border: i == 0 ? null : const Border(top: BorderSide(color: AppColors.line))),
          child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text(rows[i][0], style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w600)),
            Text(rows[i][1], style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink)),
          ]),
        ),
    ];
  }

  Widget _field(String label, String hint) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5, color: AppColors.sub)),
            const SizedBox(height: 6),
            TextField(
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
            ),
          ],
        ),
      );

  Widget _toggleRow(String label, bool on, bool first) => Container(
        padding: const EdgeInsets.symmetric(vertical: 13),
        decoration: BoxDecoration(border: first ? null : const Border(top: BorderSide(color: AppColors.line))),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.ink)),
            AppToggle(on: on),
          ],
        ),
      );
}

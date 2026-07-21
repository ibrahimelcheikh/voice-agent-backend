import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/dashboard_repository.dart';
import '../data/merchant_repository.dart';
import '../data/models.dart';
import '../l10n/strings.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class ApptsScreen extends ConsumerWidget {
  const ApptsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(languageProvider);
    final s = S.of(lang);
    ref.watch(refreshTickProvider); // rebuild after refresh / mutation
    final dash = ref.watch(dashboardRepoProvider);
    final appts = ref.read(merchantRepositoryProvider).appointments();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: ScreenHeader(title: s.v('apptsTitle'), sub: s.v('apptsSub'))),
            if (dash != null)
              _AddButton(onTap: () => _openForm(context, ref, dash)),
          ],
        ),
        const SizedBox(height: 14),
        AppCard(
          color: AppColors.cardAlt,
          padding: const EdgeInsets.all(16),
          border: Border.all(color: AppColors.line, width: 1.5, style: BorderStyle.solid),
          child: Row(
            children: [
              const Icon(Icons.calendar_today_outlined, size: 20, color: AppColors.sub),
              const SizedBox(width: 12),
              Expanded(child: Text(s.v('calDim'), style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w600, height: 1.4))),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
          child: Text(s.v('upcoming'), style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w800, fontSize: 15)),
        ),
        if (dash != null && appts.isEmpty)
          _empty(s)
        else
          for (final a in appts) ...[
            _apptCard(context, ref, dash, a, s, lang),
            const SizedBox(height: 14),
          ],
      ],
    );
  }

  Widget _empty(S s) => AppCard(
        padding: const EdgeInsets.all(28),
        child: Column(children: [
          const Icon(Icons.event_available_outlined, size: 34, color: AppColors.sub),
          const SizedBox(height: 10),
          Text(s.v('noAppts'), textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.sub, fontWeight: FontWeight.w700, height: 1.4)),
        ]),
      );

  Widget _apptCard(BuildContext context, WidgetRef ref, DashboardMerchantRepository? dash,
      Appt a, S s, String lang) {
    final cancelled = a.status == 'cancelled';
    return AppCard(
      padding: const EdgeInsets.all(18),
      child: Row(
        children: [
          Container(
            width: 58,
            height: 62,
            decoration: BoxDecoration(color: AppColors.blueSoft, borderRadius: BorderRadius.circular(16)),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(loc(a.day, lang), style: const TextStyle(color: AppColors.blueDeep, fontWeight: FontWeight.w800, fontSize: 12)),
                Text(a.date, style: const TextStyle(color: AppColors.blueDeep, fontWeight: FontWeight.w900, fontSize: 22, height: 1)),
              ],
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(a.name, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 17, color: AppColors.ink, decoration: cancelled ? TextDecoration.lineThrough : null)),
                const SizedBox(height: 2),
                Text(loc(a.svc, lang), style: const TextStyle(color: AppColors.ink, fontSize: 15)),
                const SizedBox(height: 6),
                Wrap(spacing: 8, runSpacing: 6, children: [
                  Pill(
                    bg: AppColors.cardAlt,
                    fg: AppColors.sub,
                    fontSize: 12,
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.access_time, size: 12, color: AppColors.sub),
                      const SizedBox(width: 5),
                      Text(a.time),
                    ]),
                  ),
                  Pill(
                    bg: AppColors.greenSoft,
                    fg: AppColors.green,
                    fontSize: 12,
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.auto_awesome, size: 12, color: AppColors.green),
                      const SizedBox(width: 5),
                      Text(a.via),
                    ]),
                  ),
                  if (a.status != null && a.status != 'booked') _statusPill(a.status!, s),
                ]),
              ],
            ),
          ),
          if (dash != null && a.id != null)
            PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert, color: AppColors.sub),
              onSelected: (v) {
                if (v == 'edit') _openForm(context, ref, dash, existing: a);
                if (v == 'cancel') _mutate(context, ref, () => dash.modifyAppointment(a.id!, status: 'cancelled'));
                if (v == 'delete') _mutate(context, ref, () => dash.deleteAppointment(a.id!));
              },
              itemBuilder: (_) => [
                PopupMenuItem(value: 'edit', child: Text(s.v('reschedule'))),
                if (!cancelled) PopupMenuItem(value: 'cancel', child: Text(s.v('cancel'))),
                PopupMenuItem(value: 'delete', child: Text(s.v('remove'))),
              ],
            ),
        ],
      ),
    );
  }

  Widget _statusPill(String status, S s) {
    final (bg, fg) = switch (status) {
      'rescheduled' => (AppColors.amberSoft, AppColors.amber),
      'cancelled' => (AppColors.roseSoft, AppColors.rose),
      'completed' => (AppColors.blueSoft, AppColors.blueDeep),
      _ => (AppColors.cardAlt, AppColors.sub),
    };
    return Pill(bg: bg, fg: fg, fontSize: 12, child: Text(s.v(status) == status ? status : s.v(status)));
  }

  Future<void> _mutate(BuildContext context, WidgetRef ref, Future<void> Function() op) async {
    try {
      await op();
      ref.read(refreshTickProvider.notifier).state++;
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  void _openForm(BuildContext context, WidgetRef ref, DashboardMerchantRepository dash, {Appt? existing}) {
    final lang = ref.read(languageProvider);
    final s = S.of(lang);
    final services = ref.read(merchantRepositoryProvider).services();
    final nameC = TextEditingController(text: existing?.name ?? '');
    final phoneC = TextEditingController(text: '');
    final dateC = TextEditingController(text: existing?.date ?? '');
    final timeC = TextEditingController(text: existing?.time ?? '18:00');
    String? service = existing != null ? loc(existing.svc, 'en') : (services.isNotEmpty ? services.first.en : null);
    final editing = existing != null;

    showDialog(
      context: context,
      builder: (dctx) => StatefulBuilder(
        builder: (dctx, setLocal) => AlertDialog(
          backgroundColor: AppColors.card,
          title: Text(editing ? s.v('reschedule') : s.v('addAppt')),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              if (!editing) ...[
                TextField(controller: nameC, decoration: InputDecoration(labelText: s.v('fName'))),
                TextField(controller: phoneC, decoration: InputDecoration(labelText: s.v('fPhone')), keyboardType: TextInputType.phone),
              ],
              DropdownButtonFormField<String>(
                initialValue: service,
                isExpanded: true,
                decoration: InputDecoration(labelText: s.v('fService')),
                items: [for (final sv in services) DropdownMenuItem(value: sv.en, child: Text(sv.en))],
                onChanged: (v) => setLocal(() => service = v),
              ),
              TextField(controller: dateC, decoration: const InputDecoration(labelText: 'Date (YYYY-MM-DD)')),
              TextField(controller: timeC, decoration: const InputDecoration(labelText: 'Time (HH:MM)')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(dctx).pop(), child: Text(s.v('cancel'))),
            FilledButton(
              onPressed: () {
                Navigator.of(dctx).pop();
                if (editing) {
                  _mutate(context, ref, () => dash.modifyAppointment(existing.id!,
                      date: dateC.text.trim(), time: timeC.text.trim(), service: service));
                } else {
                  _mutate(context, ref, () => dash.createAppointment(
                      name: nameC.text.trim(), phone: phoneC.text.trim(),
                      service: service, date: dateC.text.trim(), time: timeC.text.trim()));
                }
              },
              child: Text(s.v('save')),
            ),
          ],
        ),
      ),
    );
  }
}

class _AddButton extends StatelessWidget {
  const _AddButton({required this.onTap});
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
        decoration: BoxDecoration(color: AppColors.blue, borderRadius: BorderRadius.circular(999)),
        child: const Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.add, size: 18, color: Colors.white),
          SizedBox(width: 6),
          Text('Add', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
        ]),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models.dart';
import '../data/ops_repository.dart';
import '../state/app_state.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';

class TicketsScreen extends ConsumerWidget {
  const TicketsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final desktop = MediaQuery.of(context).size.width >= 900;
    final filter = ref.watch(ticketFilterProvider);
    final all = ref.read(opsRepositoryProvider).tickets();
    final list = all.where((t) => filter == 'all' || t.status == filter).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Head(title: 'Tickets', sub: 'Support requests from merchants.', right: PillButton.primary('New ticket', icon: Icons.add)),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final f in const [['all', 'All'], ['open', 'Open'], ['in_progress', 'In progress'], ['resolved', 'Resolved']])
            _filterChip(ref, f[0], f[1], filter == f[0]),
        ]),
        const SizedBox(height: 18),
        if (desktop)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Row(children: const [
              Expanded(flex: 14, child: Text('Subject', style: _hdr)),
              Expanded(flex: 10, child: Text('Merchant', style: _hdr)),
              Expanded(flex: 8, child: Text('Status', style: _hdr)),
              Expanded(flex: 7, child: Text('Priority', style: _hdr)),
              Expanded(flex: 8, child: Text('Agent', style: _hdr)),
            ]),
          ),
        if (desktop) const SizedBox(height: 10),
        for (final tk in list) ...[
          desktop ? _rowCard(tk) : _mobileCard(tk),
          const SizedBox(height: 12),
        ],
      ],
    );
  }

  static const _hdr = TextStyle(color: AppColors.sub, fontWeight: FontWeight.w700, fontSize: 12.5);

  Color _pri(String p) => {'high': AppColors.rose, 'medium': AppColors.amber, 'low': AppColors.sub}[p]!;

  Widget _rowCard(Ticket tk) {
    final st = ticketStatus(tk.status);
    return AppCard(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            flex: 14,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(tk.subject, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.ink)),
                Text('${tk.id} · ${tk.time}', style: const TextStyle(color: AppColors.sub, fontSize: 12.5)),
              ],
            ),
          ),
          Expanded(flex: 10, child: Text(tk.merchant, style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.ink))),
          Expanded(flex: 8, child: Align(alignment: Alignment.centerLeft, child: Pill(bg: st.bg, fg: st.fg, child: Text(st.label)))),
          Expanded(flex: 7, child: Text(_cap(tk.pri), style: TextStyle(fontWeight: FontWeight.w800, color: _pri(tk.pri)))),
          Expanded(flex: 8, child: Text(tk.agent, style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.ink))),
        ],
      ),
    );
  }

  Widget _mobileCard(Ticket tk) {
    final st = ticketStatus(tk.status);
    return AppCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(child: Text(tk.subject, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: AppColors.ink))),
              const SizedBox(width: 10),
              Pill(bg: st.bg, fg: st.fg, child: Text(st.label)),
            ],
          ),
          const SizedBox(height: 4),
          Text('${tk.merchant} · ${tk.id} · ${tk.time}', style: const TextStyle(color: AppColors.sub, fontSize: 13)),
          const SizedBox(height: 8),
          Row(children: [
            Pill(bg: AppColors.cardAlt, fg: _pri(tk.pri), fontSize: 11, child: Text('${tk.pri} priority')),
            const SizedBox(width: 8),
            Pill(bg: AppColors.cardAlt, fg: AppColors.sub, fontSize: 11, child: Text(tk.agent == '—' ? 'Unassigned' : tk.agent)),
          ]),
        ],
      ),
    );
  }

  String _cap(String s) => s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);

  Widget _filterChip(WidgetRef ref, String k, String label, bool on) {
    return InkWell(
      onTap: () => ref.read(ticketFilterProvider.notifier).state = k,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
        decoration: BoxDecoration(color: on ? AppColors.ink : AppColors.card, borderRadius: BorderRadius.circular(999)),
        child: Text(label, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: on ? Colors.white : AppColors.ink)),
      ),
    );
  }
}

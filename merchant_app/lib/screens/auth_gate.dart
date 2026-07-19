import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api_client.dart';
import '../data/api_merchant_repository.dart';
import '../data/merchant_repository.dart';
import '../theme/tokens.dart';
import '../widgets/ui.dart';
import 'shell.dart';

/// Shown only in API mode (USE_MOCK=false). Logs the merchant in, hydrates the API
/// repository, then swaps it into [merchantRepositoryProvider] and shows the dashboard.
class AuthGate extends ConsumerStatefulWidget {
  const AuthGate({super.key});
  @override
  ConsumerState<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends ConsumerState<AuthGate> {
  final _email = TextEditingController(text: 'merchant@atlasprimex.ai');
  final _password = TextEditingController(text: 'demo1234');
  bool _busy = false;
  bool _ready = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    setState(() { _busy = true; _error = null; });
    try {
      final api = ref.read(apiClientProvider);
      final user = await api.login(_email.text.trim(), _password.text);
      final tenantId = user['tenant_id'] as String?;
      final repo = ApiMerchantRepository(api, tenantId);
      await repo.hydrate();
      ref.read(merchantRepositoryProvider.notifier).state = repo;
      setState(() => _ready = true);
    } catch (e) {
      setState(() => _error = 'Login failed — check the backend is running at $kApiBase. ($e)');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_ready) return const MerchantShell();
    return Scaffold(
      backgroundColor: AppColors.bg,
      body: Center(
        child: SingleChildScrollView(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: AppCard(
                padding: const EdgeInsets.all(28),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Image.asset('assets/logo-mark.png', width: 40, height: 40),
                      const SizedBox(width: 10),
                      const Text.rich(TextSpan(
                        style: TextStyle(fontWeight: FontWeight.w900, fontSize: 24),
                        children: [
                          TextSpan(text: 'Atlas', style: TextStyle(color: AppColors.ink)),
                          TextSpan(text: 'Prime', style: TextStyle(color: AppColors.blue)),
                          TextSpan(text: 'X', style: TextStyle(color: AppColors.blueDeep)),
                        ],
                      )),
                    ]),
                    const SizedBox(height: 6),
                    const Text('Merchant sign in', textAlign: TextAlign.center, style: TextStyle(color: AppColors.sub)),
                    const SizedBox(height: 20),
                    _field(_email, 'Email'),
                    const SizedBox(height: 12),
                    _field(_password, 'Password', obscure: true),
                    if (_error != null) ...[
                      const SizedBox(height: 12),
                      Text(_error!, style: const TextStyle(color: AppColors.rose, fontSize: 13)),
                    ],
                    const SizedBox(height: 18),
                    _busy
                        ? const Center(child: Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator()))
                        : PillButton.primary('Sign in', icon: Icons.login, fullWidth: true, onTap: _login),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _field(TextEditingController c, String hint, {bool obscure = false}) => TextField(
        controller: c,
        obscureText: obscure,
        style: const TextStyle(fontSize: 15, color: AppColors.ink),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: const TextStyle(color: AppColors.sub),
          filled: true,
          fillColor: AppColors.cardAlt,
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.line, width: 1.5)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.blue, width: 1.5)),
        ),
      );
}

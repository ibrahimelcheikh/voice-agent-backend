import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:primeops_app/main.dart';

void main() {
  testWidgets('PrimeOps app boots', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: PrimeOpsApp()));
    await tester.pump();
    expect(find.byType(PrimeOpsApp), findsOneWidget);
  });
}

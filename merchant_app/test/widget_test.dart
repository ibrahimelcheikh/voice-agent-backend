import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:merchant_app/main.dart';

void main() {
  testWidgets('Merchant app boots (mock fallback)', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: MerchantApp(useMock: true)));
    await tester.pump();
    expect(find.byType(MerchantApp), findsOneWidget);
  });
}

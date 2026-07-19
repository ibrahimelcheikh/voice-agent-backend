import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_client.dart';
import 'models.dart';
import 'mock_data.dart';

/// Repository layer for PrimeOps. Screens read data through this interface;
/// Phase 4 adds an `ApiOpsRepository` selected by the [kUseMockData] flag.
/// PrimeOps sees ALL tenants (unlike the merchant app, which is tenant-scoped).
abstract class OpsRepository {
  List<Merchant> merchants();
  List<OpsAlert> alerts();
  List<Ticket> tickets();
  List<OpsUser> users();
  List<int> fleetVolume();
}

class MockOpsRepository implements OpsRepository {
  const MockOpsRepository();
  @override
  List<Merchant> merchants() => kMerchants;
  @override
  List<OpsAlert> alerts() => kAlerts;
  @override
  List<Ticket> tickets() => kTickets;
  @override
  List<OpsUser> users() => kUsers;
  @override
  List<int> fleetVolume() => kFleetVol;
}

/// Phase 4 flag. Default true → bundled mock data. Build with
/// `--dart-define=USE_MOCK=false --dart-define=API_BASE=https://…` to run against
/// the live /api/v1 backend (operator login gate appears).
const bool kUseMockData = bool.fromEnvironment('USE_MOCK', defaultValue: true);

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

/// Active repository. Mock by default; the login gate swaps in a hydrated
/// [ApiOpsRepository] in API mode. Screens read it synchronously either way.
final opsRepositoryProvider =
    StateProvider<OpsRepository>((ref) => const MockOpsRepository());

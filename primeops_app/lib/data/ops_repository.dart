import 'package:flutter_riverpod/flutter_riverpod.dart';
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

const bool kUseMockData = bool.fromEnvironment('USE_MOCK', defaultValue: true);

final opsRepositoryProvider = Provider<OpsRepository>((ref) {
  // Phase 4: return kUseMockData ? const MockOpsRepository() : ApiOpsRepository(...);
  return const MockOpsRepository();
});

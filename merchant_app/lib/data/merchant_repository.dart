import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_client.dart';
import 'models.dart';
import 'mock_data.dart';

/// Repository layer. Every screen reads data through this interface, never from
/// the mock constants directly. Phase 4 adds an `ApiMerchantRepository` and the
/// [kUseMockData] flag (or a `--dart-define`) selects which implementation the
/// [merchantRepositoryProvider] returns — screens don't change.
abstract class MerchantRepository {
  List<Branch> branches();
  List<Service> services();
  Service? serviceById(String id);
  List<Convo> conversations();
  List<Faq> faqs();
  List<Appt> appointments();
  List<Holiday> holidays();
  List<int> callVolume();
  Map<String, List<Report>> reports();
}

class MockMerchantRepository implements MerchantRepository {
  const MockMerchantRepository();

  @override
  List<Branch> branches() => kBranches;
  @override
  List<Service> services() => kServices;
  @override
  Service? serviceById(String id) {
    for (final s in kServices) {
      if (s.id == id) return s;
    }
    return null;
  }

  @override
  List<Convo> conversations() => kConvos;
  @override
  List<Faq> faqs() => kFaqs;
  @override
  List<Appt> appointments() => kAppts;
  @override
  List<Holiday> holidays() => kHolidays;
  @override
  List<int> callVolume() => kVol;
  @override
  Map<String, List<Report>> reports() => kReports;
}

/// Phase 4 flag. Default true → bundled mock data (works with no backend).
/// Build with `--dart-define=USE_MOCK=false --dart-define=API_BASE=https://…` to run
/// the app against the live /api/v1 backend (a login screen then appears).
const bool kUseMockData = bool.fromEnvironment('USE_MOCK', defaultValue: true);

/// Shared authenticated API client.
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

/// The active repository. Starts as the mock; in API mode the login gate replaces it
/// with a hydrated [ApiMerchantRepository]. Screens read it synchronously either way.
final merchantRepositoryProvider =
    StateProvider<MerchantRepository>((ref) => const MockMerchantRepository());

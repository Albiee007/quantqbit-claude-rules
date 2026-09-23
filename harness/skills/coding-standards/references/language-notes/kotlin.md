# Kotlin / Android Notes

## Idioms

- `val` by default; `var` only when reassigned. Immutable collections (`List`, `Map`) in APIs; `MutableList` stays private.
- Null safety: model absence with `T?`; use `?.`, `?:`, `let`. Avoid `!!` — treat each as a bug unless justified by a comment.
- `data class` for values; `@JvmInline value class` for typed ids/units (`value class UserId(val raw: String)`).
- `sealed interface`/`sealed class` for states and results; `when` as an expression (exhaustive, no `else` so new cases fail compilation).
  ```kotlin
  sealed interface LoadState<out T> {
      data object Loading : LoadState<Nothing>
      data class Success<T>(val data: T) : LoadState<T>
      data class Error(val cause: Throwable) : LoadState<Nothing>
  }
  ```
- `object` for true singletons without state; prefer constructor-injected instances for anything stateful or I/O.
- Extension functions for local convenience — not to hide business logic or add behavior to types you own.
- Scope functions: `apply` for configuration, `let` for null handling/mapping, `also` for side effects; don't nest them.
- Default and named arguments instead of overloads/builders.
- `require()` for argument checks, `check()` for state, `error()` for impossible branches.
- `Result`/sealed types for expected failures; exceptions for bugs and infrastructure errors.
- Top-level functions are fine; no `Utils` classes.

## Coroutines & Flow

- Structured concurrency: launch in a lifecycle-bound scope (`viewModelScope`, `lifecycleScope`, injected `CoroutineScope`). Never `GlobalScope`.
- `suspend` functions are main-safe: switch dispatchers inside (`withContext(Dispatchers.IO)`), inject dispatchers for testability.
- Never catch `CancellationException` without rethrowing; `runCatching` swallows it — avoid in suspend code or rethrow.
- `coroutineScope { }` for parallel decomposition; `supervisorScope` when children fail independently.
- Expose `StateFlow` for UI state, `SharedFlow`/`Channel` for one-shot events (or model events as state). Collect with `repeatOnLifecycle`/`collectAsStateWithLifecycle`.
- Cold `Flow` for streams; `stateIn`/`shareIn` with `WhileSubscribed(5_000)` to share upstream work.
- Tests: `runTest`, `StandardTestDispatcher`, Turbine for Flow assertions.

## Android specifics

- Architecture per official guide: UI (Compose/View) → ViewModel (state holder) → domain (optional) → data (repositories). Unidirectional data flow.
- No `Context`/`View`/`Activity` references in ViewModels (leaks); use `Application` context only via DI when needed.
- Compose: state hoisting; stable parameters; `remember`/`rememberSaveable`; side effects via `LaunchedEffect` keyed correctly; no work in composition.
- DI with Hilt/Koin per project; constructor injection.
- Secrets: never in `BuildConfig`/resources for anything truly secret; tokens in EncryptedSharedPreferences/DataStore + Keystore.
- Main thread: no disk/network (StrictMode in debug).
- R8/ProGuard keep rules for reflection/serialization.

## Pitfalls

- Platform types from Java (`String!`) — annotate or check nullability at the boundary.
- `lateinit` hides initialization bugs; prefer constructor params or `by lazy`.
- `data class` with mutable `var` properties used as map keys.
- `equals` on arrays inside data classes compares references.
- Leaking coroutines from `init {}` blocks without a scope.
- `Flow.collect` in `onCreate` without lifecycle awareness keeps collecting in background.

## Tooling

- ktlint/detekt/Android Lint per project; `./gradlew check` (or module-specific `test`, `lint`) before finishing.
- Version catalogs (`libs.versions.toml`) for dependencies.

## Sources

- Kotlin coding conventions: https://kotlinlang.org/docs/coding-conventions.html
- Android app architecture guide: https://developer.android.com/topic/architecture
- Coroutines best practices: https://developer.android.com/kotlin/coroutines/coroutines-best-practices

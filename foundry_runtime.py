"""Foundry Local model yaşam döngüsü için küçük ve test edilebilir katman."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class FoundryRuntimeError(Exception):
    """Foundry runtime katmanındaki proje hatalarının taban sınıfı."""


class RuntimeInitializationError(FoundryRuntimeError):
    """Foundry Local manager başlatılamadığında üretilir."""


class RuntimeNotInitializedError(FoundryRuntimeError):
    """Bir model işlemi initialize öncesinde istendiğinde üretilir."""


class ModelUnavailableError(FoundryRuntimeError):
    """Yapılandırılmış model offline kullanım için hazır olmadığında üretilir."""


class ModelDownloadError(FoundryRuntimeError):
    """Açıkça izin verilen model indirmesi başarısız olduğunda üretilir."""


class ModelLoadError(FoundryRuntimeError):
    """Model belleğe yüklenemediğinde üretilir."""


class ClientCreationError(FoundryRuntimeError):
    """Chat veya embedding client oluşturulamadığında üretilir."""


class RuntimeCleanupError(FoundryRuntimeError):
    """Yüklenen modellerden biri veya birkaçı kapatılamadığında üretilir."""


@dataclass(frozen=True)
class FoundryRuntimeConfig:
    """Uygulamanın kullanmayı planladığı Foundry Local alias yapılandırması."""

    app_name: str = "foundry_local_samples"
    embedding_model_alias: str = "qwen3-embedding-0.6b"
    chat_model_alias: str = "qwen3-1.7b"

    def __post_init__(self) -> None:
        values = {
            "app_name": self.app_name,
            "embedding_model_alias": self.embedding_model_alias,
            "chat_model_alias": self.chat_model_alias,
        }
        for field_name, value in values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} boş olmamalıdır.")


def _load_sdk() -> tuple[type[Any], type[Any]]:
    """SDK sınıflarını yalnızca initialize açıkça istendiğinde import et."""
    from foundry_local_sdk import Configuration, FoundryLocalManager

    return Configuration, FoundryLocalManager


class FoundryRuntime:
    """Foundry manager, model, client ve cleanup yaşam döngüsünü yönetir.

    Foundry Local manager process-global bir singleton'dır. SDK daha önce
    initialize edilmişse mevcut manager yeniden kullanılır; bu wrapper mevcut
    manager'ın hangi config ile oluşturulduğunu public SDK üzerinden doğrulamaz.
    Aynı process içindeki farklı runtime configleri global manager'ı yeniden
    yapılandırmaz.
    """

    def __init__(
        self,
        config: FoundryRuntimeConfig | None = None,
        sdk_loader: Callable[[], tuple[type[Any], type[Any]]] | None = None,
    ) -> None:
        self.config = config or FoundryRuntimeConfig()
        self._sdk_loader = sdk_loader or _load_sdk
        self._manager: Any | None = None
        self._models: dict[str, Any] = {}
        self._clients: dict[tuple[str, str], Any] = {}
        self._loaded_models: list[Any] = []
        self._closed = False
        self._cleanup_pending = False

    @property
    def is_initialized(self) -> bool:
        """Bu runtime nesnesinin initialize edilip edilmediğini gösterir."""
        return (
            self._manager is not None
            and not self._closed
            and not self._cleanup_pending
        )

    def initialize(self) -> None:
        """Process-global manager'ı başlat veya mevcut manager'ı yeniden kullan.

        Mevcut global manager'ın config'i public SDK üzerinden doğrulanmaz ve bu
        runtime'ın config'iyle yeniden yapılandırılmaz.
        """
        if self.is_initialized:
            return
        if self._closed:
            raise RuntimeInitializationError("Kapatılmış runtime yeniden başlatılamaz.")
        if self._cleanup_pending:
            raise RuntimeInitializationError(
                "Cleanup tamamlanmadan runtime yeniden başlatılamaz."
            )

        try:
            configuration_type, manager_type = self._sdk_loader()
            configuration = configuration_type(app_name=self.config.app_name)
            if getattr(manager_type, "instance", None) is None:
                manager_type.initialize(configuration)
            manager = manager_type.instance
            if manager is None:
                raise RuntimeError("SDK manager instance oluşturmadı.")
        except Exception as exc:
            raise RuntimeInitializationError(
                f"Foundry Local runtime '{self.config.app_name}' için başlatılamadı."
            ) from exc

        self._manager = manager

    def get_embedding_client(
        self,
        *,
        allow_download: bool = False,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Any:
        """Yapılandırılmış embedding modeli için client döndür."""
        return self._get_client(
            alias=self.config.embedding_model_alias,
            client_kind="embedding",
            allow_download=allow_download,
            progress_callback=progress_callback,
        )

    def get_chat_client(
        self,
        *,
        allow_download: bool = False,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Any:
        """Yapılandırılmış chat modeli için client döndür."""
        return self._get_client(
            alias=self.config.chat_model_alias,
            client_kind="chat",
            allow_download=allow_download,
            progress_callback=progress_callback,
        )

    def _get_client(
        self,
        *,
        alias: str,
        client_kind: str,
        allow_download: bool,
        progress_callback: Callable[[float], None] | None,
    ) -> Any:
        manager = self._require_manager()
        client_key = (alias, client_kind)
        if client_key in self._clients:
            return self._clients[client_key]

        model = self._resolve_model(manager, alias)
        self._prepare_model(
            model,
            alias=alias,
            allow_download=allow_download,
            progress_callback=progress_callback,
        )

        try:
            if client_kind == "embedding":
                client = model.get_embedding_client()
            else:
                client = model.get_chat_client()
        except Exception as exc:
            raise ClientCreationError(
                f"'{alias}' modeli için {client_kind} client oluşturulamadı."
            ) from exc

        self._clients[client_key] = client
        return client

    def _require_manager(self) -> Any:
        if not self.is_initialized:
            if self._cleanup_pending:
                raise RuntimeNotInitializedError(
                    "Runtime cleanup bekliyor; önce FoundryRuntime.close() yeniden "
                    "çağrılmalıdır."
                )
            raise RuntimeNotInitializedError(
                "Model client istemeden önce FoundryRuntime.initialize() çağrılmalıdır."
            )
        return self._manager

    def _resolve_model(self, manager: Any, alias: str) -> Any:
        if alias in self._models:
            return self._models[alias]

        try:
            model = manager.catalog.get_model(alias)
        except Exception as exc:
            raise ModelUnavailableError(
                f"Yapılandırılmış model alias'ı '{alias}' katalogdan çözülemedi."
            ) from exc
        if model is None:
            raise ModelUnavailableError(
                f"Yapılandırılmış model alias'ı '{alias}' katalogda bulunamadı."
            )

        self._models[alias] = model
        return model

    def _prepare_model(
        self,
        model: Any,
        *,
        alias: str,
        allow_download: bool,
        progress_callback: Callable[[float], None] | None,
    ) -> None:
        try:
            is_cached = model.is_cached
        except Exception as exc:
            raise ModelUnavailableError(
                f"'{alias}' modelinin yerel cache durumu okunamadı."
            ) from exc

        if not is_cached:
            if not allow_download:
                raise ModelUnavailableError(
                    f"'{alias}' modeli yerel cache içinde değil; offline modda indirme "
                    "yapılmaz. İlk kurulumda allow_download=True açıkça verilmelidir."
                )
            try:
                model.download(progress_callback=progress_callback)
            except Exception as exc:
                raise ModelDownloadError(
                    f"'{alias}' modeli açık izinle indirilirken hata oluştu."
                ) from exc

        try:
            already_loaded = model.is_loaded
            if not already_loaded:
                model.load()
                self._loaded_models.append(model)
        except Exception as exc:
            mode_hint = (
                "İlk kurulum için allow_download=True gerekebilir."
                if not allow_download
                else "Model indirildikten sonra yüklenemedi."
            )
            raise ModelLoadError(f"'{alias}' modeli yüklenemedi. {mode_hint}") from exc

    def close(self) -> None:
        """Bu runtime tarafından yüklenen bütün modelleri kapat."""
        if self._closed:
            return

        errors: list[Exception] = []
        failed_models: list[Any] = []
        for model in reversed(list(self._loaded_models)):
            try:
                model.unload()
            except Exception as exc:
                errors.append(exc)
                failed_models.append(model)

        if errors:
            # Listeyi özgün sahiplik sırasıyla koru. Sonraki close() yalnızca
            # başarısız modelleri yeniden dener.
            self._loaded_models = list(reversed(failed_models))
            self._cleanup_pending = True
            raise RuntimeCleanupError(
                f"Foundry runtime kapatılırken {len(errors)} model unload edilemedi."
            ) from errors[0]

        self._loaded_models.clear()
        self._clients.clear()
        self._models.clear()
        self._manager = None
        self._cleanup_pending = False
        self._closed = True

    def __enter__(self) -> FoundryRuntime:
        self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        if exc_type is None:
            self.close()
        else:
            try:
                self.close()
            except RuntimeCleanupError as cleanup_error:
                exc.add_note(
                    "Context cleanup ayrıca başarısız oldu: "
                    f"{type(cleanup_error).__name__}: {cleanup_error}"
                )
        return False

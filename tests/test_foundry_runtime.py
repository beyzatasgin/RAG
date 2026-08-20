"""Foundry runtime wrapper sözleşmesi için SDK'sız fake testleri."""

import importlib
import sys

import pytest

from foundry_runtime import (
    ClientCreationError,
    FoundryRuntime,
    FoundryRuntimeConfig,
    ModelDownloadError,
    ModelLoadError,
    ModelUnavailableError,
    RuntimeCleanupError,
    RuntimeInitializationError,
    RuntimeNotInitializedError,
)


class FakeConfiguration:
    def __init__(self, app_name, **kwargs):
        self.app_name = app_name
        self.kwargs = kwargs


class FakeModel:
    def __init__(self, alias, *, cached=True, loaded=False):
        self.alias = alias
        self._is_cached = cached
        self.is_loaded = loaded
        self.download_calls = 0
        self.load_calls = 0
        self.unload_calls = 0
        self.embedding_client_calls = 0
        self.chat_client_calls = 0
        self.fail_download = False
        self.fail_load = False
        self.fail_unload = False
        self.fail_client = False
        self.fail_cache_check = False

    @property
    def is_cached(self):
        if self.fail_cache_check:
            raise RuntimeError("cache check failed")
        return self._is_cached

    def download(self, progress_callback=None):
        self.download_calls += 1
        if self.fail_download:
            raise RuntimeError("download failed")
        self._is_cached = True
        if progress_callback:
            progress_callback(100.0)

    def load(self):
        self.load_calls += 1
        if self.fail_load:
            raise RuntimeError("load failed")
        self.is_loaded = True

    def unload(self):
        self.unload_calls += 1
        if self.fail_unload:
            raise RuntimeError("unload failed")
        self.is_loaded = False

    def get_embedding_client(self):
        self.embedding_client_calls += 1
        if self.fail_client:
            raise RuntimeError("client failed")
        return ("embedding", self.alias)

    def get_chat_client(self):
        self.chat_client_calls += 1
        if self.fail_client:
            raise RuntimeError("client failed")
        return ("chat", self.alias)


class FakeCatalog:
    def __init__(self, models):
        self.models = models
        self.get_model_calls = []
        self.fail = False

    def get_model(self, alias):
        self.get_model_calls.append(alias)
        if self.fail:
            raise RuntimeError("catalog failed")
        return self.models.get(alias)


def make_sdk(
    models=None,
    *,
    initialize_error=None,
    initialize_outcomes=None,
    existing_manager=None,
):
    catalog = FakeCatalog(models or {})
    outcomes = list(initialize_outcomes or [])

    class FakeManager:
        instance = existing_manager
        initialize_calls = 0
        configurations = []

        @staticmethod
        def initialize(configuration):
            FakeManager.initialize_calls += 1
            FakeManager.configurations.append(configuration)
            if outcomes:
                outcome = outcomes.pop(0)
                if outcome is not None:
                    raise outcome
            if initialize_error:
                raise initialize_error
            FakeManager.instance = type("Manager", (), {"catalog": catalog})()

    return catalog, FakeManager, lambda: (FakeConfiguration, FakeManager)


@pytest.mark.parametrize(
    ("field", "kwargs"),
    [
        ("app_name", {"app_name": " "}),
        ("embedding_model_alias", {"embedding_model_alias": ""}),
        ("chat_model_alias", {"chat_model_alias": ""}),
        ("app_data_dir", {"app_data_dir": " "}),
        ("model_cache_dir", {"model_cache_dir": ""}),
        ("logs_dir", {"logs_dir": "\t"}),
    ],
)
def test_config_rejects_empty_values(field, kwargs):
    with pytest.raises(ValueError, match=field):
        FoundryRuntimeConfig(**kwargs)


def test_importing_module_does_not_import_or_initialize_sdk(monkeypatch):
    monkeypatch.delitem(sys.modules, "foundry_runtime", raising=False)
    monkeypatch.delitem(sys.modules, "foundry_local_sdk", raising=False)

    imported = importlib.import_module("foundry_runtime")
    imported.FoundryRuntime()

    assert imported.FoundryRuntime is not None
    assert "foundry_local_sdk" not in sys.modules


def test_constructing_runtime_does_not_load_sdk():
    loader_calls = []
    FoundryRuntime(sdk_loader=lambda: loader_calls.append(True))
    assert loader_calls == []


def test_initialize_is_idempotent():
    _, manager_type, loader = make_sdk()
    runtime = FoundryRuntime(sdk_loader=loader)

    runtime.initialize()
    runtime.initialize()

    assert manager_type.initialize_calls == 1
    assert runtime.is_initialized


def test_initialize_forwards_explicit_paths_to_configuration():
    _, manager_type, loader = make_sdk()
    config = FoundryRuntimeConfig(
        app_data_dir="app-data",
        model_cache_dir="shared-cache",
        logs_dir="logs",
    )

    FoundryRuntime(config, loader).initialize()

    created = manager_type.configurations[0]
    assert created.kwargs == {
        "app_data_dir": "app-data",
        "model_cache_dir": "shared-cache",
        "logs_dir": "logs",
    }


def test_initialize_omits_none_paths_to_preserve_sdk_defaults():
    _, manager_type, loader = make_sdk()

    FoundryRuntime(sdk_loader=loader).initialize()

    assert manager_type.configurations[0].kwargs == {}


def test_initialize_error_is_chained():
    original = RuntimeError("native failure")
    _, _, loader = make_sdk(initialize_error=original)

    with pytest.raises(RuntimeInitializationError) as error:
        FoundryRuntime(sdk_loader=loader).initialize()

    assert error.value.__cause__ is original


def test_initialize_can_retry_after_failure():
    original = RuntimeError("first failure")
    _, manager_type, loader = make_sdk(initialize_outcomes=[original, None])
    runtime = FoundryRuntime(sdk_loader=loader)

    with pytest.raises(RuntimeInitializationError):
        runtime.initialize()
    runtime.initialize()

    assert manager_type.initialize_calls == 2
    assert runtime.is_initialized


def test_existing_global_manager_is_reused_without_initialize():
    existing = type("Manager", (), {"catalog": FakeCatalog({})})()
    _, manager_type, loader = make_sdk(existing_manager=existing)
    runtime = FoundryRuntime(sdk_loader=loader)

    runtime.initialize()

    assert manager_type.initialize_calls == 0
    assert runtime.is_initialized


def test_different_wrapper_config_does_not_reinitialize_existing_manager():
    existing = type("Manager", (), {"catalog": FakeCatalog({})})()
    _, manager_type, loader = make_sdk(existing_manager=existing)
    runtime = FoundryRuntime(FoundryRuntimeConfig(app_name="second-app"), loader)

    runtime.initialize()

    assert manager_type.initialize_calls == 0
    assert manager_type.configurations == []


def test_manager_instance_access_error_is_chained():
    original = RuntimeError("instance unavailable")

    class ExplodingManagerMeta(type):
        @property
        def instance(cls):
            raise original

    class ExplodingManager(metaclass=ExplodingManagerMeta):
        @staticmethod
        def initialize(configuration):
            pytest.fail("initialize çağrılmamalı")

    runtime = FoundryRuntime(
        sdk_loader=lambda: (FakeConfiguration, ExplodingManager)
    )

    with pytest.raises(RuntimeInitializationError) as error:
        runtime.initialize()

    assert error.value.__cause__ is original


def test_client_before_initialize_is_rejected():
    runtime = FoundryRuntime(sdk_loader=lambda: pytest.fail("loader called"))
    with pytest.raises(RuntimeNotInitializedError):
        runtime.get_embedding_client()


def test_offline_mode_never_downloads_uncached_model():
    model = FakeModel("embedding", cached=False)
    _, _, loader = make_sdk({"embedding": model})
    config = FoundryRuntimeConfig(embedding_model_alias="embedding")
    runtime = FoundryRuntime(config, loader)
    runtime.initialize()

    with pytest.raises(ModelUnavailableError, match="offline"):
        runtime.get_embedding_client(allow_download=False)

    assert model.download_calls == 0
    assert model.load_calls == 0


def test_cached_model_is_not_downloaded_when_download_is_allowed():
    model = FakeModel("embedding", cached=True)
    _, _, loader = make_sdk({"embedding": model})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
    )
    runtime.initialize()

    runtime.get_embedding_client(allow_download=True)

    assert model.download_calls == 0


def test_cache_check_error_is_chained():
    model = FakeModel("embedding")
    model.fail_cache_check = True
    _, _, loader = make_sdk({"embedding": model})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
    )
    runtime.initialize()

    with pytest.raises(ModelUnavailableError) as error:
        runtime.get_embedding_client()

    assert isinstance(error.value.__cause__, RuntimeError)


def test_download_is_explicit_and_client_is_cached():
    model = FakeModel("embedding", cached=False)
    _, _, loader = make_sdk({"embedding": model})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
    )
    progress = []
    runtime.initialize()

    first = runtime.get_embedding_client(
        allow_download=True, progress_callback=progress.append
    )
    second = runtime.get_embedding_client(allow_download=True)

    assert first is second
    assert model.download_calls == 1
    assert model.load_calls == 1
    assert model.embedding_client_calls == 1
    assert progress == [100.0]


def test_embedding_and_chat_clients_use_separate_models():
    embedding = FakeModel("embedding")
    chat = FakeModel("chat")
    _, _, loader = make_sdk({"embedding": embedding, "chat": chat})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(
            embedding_model_alias="embedding", chat_model_alias="chat"
        ),
        loader,
    )
    runtime.initialize()

    assert runtime.get_embedding_client() == ("embedding", "embedding")
    assert runtime.get_chat_client() == ("chat", "chat")
    assert embedding.chat_client_calls == 0
    assert chat.embedding_client_calls == 0


def test_same_alias_uses_one_model_load_two_clients_and_one_unload():
    model = FakeModel("shared")
    catalog, _, loader = make_sdk({"shared": model})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(
            embedding_model_alias="shared", chat_model_alias="shared"
        ),
        loader,
    )
    runtime.initialize()

    assert runtime.get_embedding_client() == ("embedding", "shared")
    assert runtime.get_chat_client() == ("chat", "shared")
    runtime.close()

    assert catalog.get_model_calls == ["shared"]
    assert model.load_calls == 1
    assert model.embedding_client_calls == 1
    assert model.chat_client_calls == 1
    assert model.unload_calls == 1


def test_missing_model_is_reported():
    _, _, loader = make_sdk({})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(embedding_model_alias="missing"), loader
    )
    runtime.initialize()

    with pytest.raises(ModelUnavailableError, match="bulunamadı"):
        runtime.get_embedding_client()


def test_catalog_error_is_chained():
    catalog, _, loader = make_sdk({})
    catalog.fail = True
    runtime = FoundryRuntime(sdk_loader=loader)
    runtime.initialize()

    with pytest.raises(ModelUnavailableError) as error:
        runtime.get_embedding_client()

    assert isinstance(error.value.__cause__, RuntimeError)


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [("download", ModelDownloadError), ("load", ModelLoadError)],
)
def test_model_prepare_errors_are_chained(failure, expected_error):
    model = FakeModel("embedding", cached=failure != "download")
    setattr(model, f"fail_{failure}", True)
    _, _, loader = make_sdk({"embedding": model})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
    )
    runtime.initialize()

    with pytest.raises(expected_error) as error:
        runtime.get_embedding_client(allow_download=True)

    assert isinstance(error.value.__cause__, RuntimeError)


def test_client_creation_error_is_chained():
    model = FakeModel("embedding")
    model.fail_client = True
    _, _, loader = make_sdk({"embedding": model})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
    )
    runtime.initialize()

    with pytest.raises(ClientCreationError) as error:
        runtime.get_embedding_client()

    assert isinstance(error.value.__cause__, RuntimeError)


def test_client_error_keeps_loaded_model_available_for_cleanup():
    model = FakeModel("embedding")
    model.fail_client = True
    _, _, loader = make_sdk({"embedding": model})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
    )
    runtime.initialize()

    with pytest.raises(ClientCreationError):
        runtime.get_embedding_client()
    runtime.close()

    assert model.unload_calls == 1


def test_close_unloads_only_models_loaded_by_runtime_and_is_idempotent():
    owned = FakeModel("embedding")
    external = FakeModel("chat", loaded=True)
    _, _, loader = make_sdk({"embedding": owned, "chat": external})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(
            embedding_model_alias="embedding", chat_model_alias="chat"
        ),
        loader,
    )
    runtime.initialize()
    runtime.get_embedding_client()
    runtime.get_chat_client()

    runtime.close()
    runtime.close()

    assert owned.unload_calls == 1
    assert external.unload_calls == 0


def test_cleanup_continues_after_unload_error():
    embedding = FakeModel("embedding")
    chat = FakeModel("chat")
    embedding.fail_unload = True
    _, _, loader = make_sdk({"embedding": embedding, "chat": chat})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(
            embedding_model_alias="embedding", chat_model_alias="chat"
        ),
        loader,
    )
    runtime.initialize()
    runtime.get_embedding_client()
    runtime.get_chat_client()

    with pytest.raises(RuntimeCleanupError) as error:
        runtime.close()

    assert isinstance(error.value.__cause__, RuntimeError)
    assert embedding.unload_calls == 1
    assert chat.unload_calls == 1


def test_cleanup_retry_only_retries_failed_model_then_becomes_idempotent():
    embedding = FakeModel("embedding")
    chat = FakeModel("chat")
    embedding.fail_unload = True
    _, _, loader = make_sdk({"embedding": embedding, "chat": chat})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(
            embedding_model_alias="embedding", chat_model_alias="chat"
        ),
        loader,
    )
    runtime.initialize()
    runtime.get_embedding_client()
    runtime.get_chat_client()

    with pytest.raises(RuntimeCleanupError):
        runtime.close()
    embedding.fail_unload = False
    runtime.close()
    runtime.close()

    assert embedding.unload_calls == 2
    assert chat.unload_calls == 1


def test_client_access_is_rejected_while_cleanup_is_pending():
    model = FakeModel("embedding")
    model.fail_unload = True
    _, _, loader = make_sdk({"embedding": model})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
    )
    runtime.initialize()
    runtime.get_embedding_client()

    with pytest.raises(RuntimeCleanupError):
        runtime.close()
    with pytest.raises(RuntimeNotInitializedError, match="cleanup"):
        runtime.get_embedding_client()


def test_client_and_reinitialize_are_rejected_after_successful_close():
    model = FakeModel("embedding")
    _, _, loader = make_sdk({"embedding": model})
    runtime = FoundryRuntime(
        FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
    )
    runtime.initialize()
    runtime.get_embedding_client()
    runtime.close()

    with pytest.raises(RuntimeNotInitializedError):
        runtime.get_embedding_client()
    with pytest.raises(RuntimeInitializationError, match="Kapatılmış"):
        runtime.initialize()


def test_context_manager_cleans_up_on_success():
    model = FakeModel("embedding")
    _, _, loader = make_sdk({"embedding": model})
    with FoundryRuntime(
        FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
    ) as runtime:
        runtime.get_embedding_client()

    assert model.unload_calls == 1


def test_context_manager_cleans_up_and_preserves_body_exception():
    model = FakeModel("embedding")
    _, _, loader = make_sdk({"embedding": model})

    with pytest.raises(ValueError, match="body failure"):
        with FoundryRuntime(
            FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
        ) as runtime:
            runtime.get_embedding_client()
            raise ValueError("body failure")

    assert model.unload_calls == 1


def test_context_body_error_keeps_type_and_adds_cleanup_note():
    model = FakeModel("embedding")
    model.fail_unload = True
    _, _, loader = make_sdk({"embedding": model})

    with pytest.raises(ValueError, match="body failure") as error:
        with FoundryRuntime(
            FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
        ) as runtime:
            runtime.get_embedding_client()
            raise ValueError("body failure")

    assert any(
        "RuntimeCleanupError" in note and "unload edilemedi" in note
        for note in error.value.__notes__
    )


def test_context_success_exposes_cleanup_error():
    model = FakeModel("embedding")
    model.fail_unload = True
    _, _, loader = make_sdk({"embedding": model})

    with pytest.raises(RuntimeCleanupError):
        with FoundryRuntime(
            FoundryRuntimeConfig(embedding_model_alias="embedding"), loader
        ) as runtime:
            runtime.get_embedding_client()

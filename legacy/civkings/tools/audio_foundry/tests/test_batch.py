from tools.audio_foundry.batch import Job, run_batch
from tools.audio_foundry.review import promote, load_manifest


def test_batch_stages_and_validates(tmp_path):
    jobs = [
        Job("tts", "rome_intro", "Hail the Senate", voice="voice_rome"),
        Job("sfx", "sword_clash", "swords clashing"),
    ]
    manifest = run_batch(jobs, tmp_path / "staging", dry_run=True)
    entries = load_manifest(manifest)
    assert len(entries) == 2
    assert all(e["valid"] for e in entries)


def test_promote_only_approved(tmp_path):
    jobs = [
        Job("tts", "keep_me", "narration", voice="v1"),
        Job("sfx", "drop_me", "noise"),
    ]
    manifest = run_batch(jobs, tmp_path / "staging", dry_run=True)
    final = tmp_path / "final"
    promoted = promote(manifest, final, approved={"keep_me"})
    assert promoted == ["keep_me"]
    assert (final / "tts" / "keep_me.wav").exists()
    assert not (final / "sfx" / "drop_me.wav").exists()


def test_promote_all_valid_by_default(tmp_path):
    jobs = [Job("sfx", "a", "x"), Job("sfx", "b", "y")]
    manifest = run_batch(jobs, tmp_path / "s", dry_run=True)
    promoted = promote(manifest, tmp_path / "f")
    assert set(promoted) == {"a", "b"}
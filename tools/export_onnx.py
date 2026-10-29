"""미세조정한 문장 모델을 브라우저용 ONNX(8비트)로 바꾼다. 결과: <out>/model.onnx, <out>/model_quantized.onnx, 토크나이저·설정 파일
1) optimum 으로 변환 → 안 되면 2) torch.onnx 로 직접 변환. 어디서 실패해도 원인을 GitHub 알림으로 남긴다."""
import sys, traceback
from pathlib import Path


def note(m):
    print(m); print("::notice::" + m.replace("\n", " ## ")[:3500], flush=True)


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    note("받은 모델 파일: " + ", ".join(sorted(p.name for p in src.iterdir())))
    import torch
    from transformers import AutoModel, AutoTokenizer
    hf = AutoModel.from_pretrained(str(src)); tok = AutoTokenizer.from_pretrained(str(src))
    hf.eval()
    tok.save_pretrained(out); hf.config.save_pretrained(out)
    ok = False
    try:
        from optimum.onnxruntime import ORTModelForFeatureExtraction
        m = ORTModelForFeatureExtraction.from_pretrained(str(src), export=True)
        m.save_pretrained(str(out)); ok = (out / "model.onnx").exists()
        note(f"optimum 변환 {'성공' if ok else '파일 없음'}")
    except Exception:
        note("optimum 변환 실패: " + traceback.format_exc()[-1500:])
    if not ok:
        hf.config.return_dict = False
        enc = tok(["피부 재생 크림", "촉촉한 보습 로션입니다"], padding=True, return_tensors="pt")
        kw = {"dynamo": False} if "dynamo" in torch.onnx.export.__code__.co_varnames else {}
        torch.onnx.export(hf, (enc["input_ids"], enc["attention_mask"]), str(out / "model.onnx"),
                          input_names=["input_ids", "attention_mask"], output_names=["last_hidden_state", "pooler_output"],
                          dynamic_axes={"input_ids": {0: "b", 1: "s"}, "attention_mask": {0: "b", 1: "s"}, "last_hidden_state": {0: "b", 1: "s"}},
                          opset_version=14, do_constant_folding=True, **kw)
        hf.config.return_dict = True
        note(f"torch.onnx 직접 변환 완료 (torch {torch.__version__})")
    from onnxruntime.quantization import quantize_dynamic, QuantType
    quantize_dynamic(str(out / "model.onnx"), str(out / "model_quantized.onnx"), weight_type=QuantType.QInt8, per_channel=True)
    # 변환이 맞는지: 원래(파이토치, 평균 풀링) 임베딩과 8비트 ONNX 임베딩 비교
    import numpy as np, onnxruntime as ort
    texts = ["피부 재생 크림", "아침에 마시는 따뜻한 차", "면역력 강화에 좋아요"]
    e = tok(texts, padding=True, return_tensors="pt")
    with torch.no_grad():
        h0 = hf(**e)[0].numpy()
    m0 = e["attention_mask"].numpy()[..., None]
    ref = (h0 * m0).sum(1) / m0.sum(1); ref /= np.linalg.norm(ref, axis=1, keepdims=True)
    s = ort.InferenceSession(str(out / "model_quantized.onnx"), providers=["CPUExecutionProvider"])
    names = {i.name for i in s.get_inputs()}
    feed = {"input_ids": e["input_ids"].numpy().astype(np.int64), "attention_mask": e["attention_mask"].numpy().astype(np.int64)}
    if "token_type_ids" in names: feed["token_type_ids"] = np.zeros_like(feed["input_ids"])
    h = s.run(None, feed)[0]
    v = (h * m0).sum(1) / m0.sum(1); v /= np.linalg.norm(v, axis=1, keepdims=True)
    note(f"변환 확인: 원래 모델과 8비트 ONNX 임베딩 코사인 {[round(float(x), 4) for x in (ref * v).sum(1)]}")
    note("결과 파일: " + ", ".join(sorted(p.name for p in out.iterdir())))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        note("변환 실패: " + traceback.format_exc()[-2500:]); sys.exit(1)

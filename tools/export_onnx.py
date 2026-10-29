"""미세조정한 문장 모델을 브라우저용 ONNX(8비트)로 바꾼다. 결과: <out>/model.onnx, <out>/model_quantized.onnx, 토크나이저 파일
1) optimum 으로 변환 → 안 되면 2) torch.onnx 로 직접 변환. 오류는 GitHub 알림으로 남긴다."""
import sys, traceback
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
def note(m): print(m); print("::notice::" + m.replace("\n", " ## ")[:3500])

from sentence_transformers import SentenceTransformer
st = SentenceTransformer(str(src), device="cpu")
hf, tok = st[0].auto_model, st[0].tokenizer
hfdir = out.parent / (out.name + "_hf")
hf.save_pretrained(hfdir); tok.save_pretrained(hfdir); tok.save_pretrained(out)
ok = False
try:
    from optimum.onnxruntime import ORTModelForFeatureExtraction
    m = ORTModelForFeatureExtraction.from_pretrained(str(hfdir), export=True)
    m.save_pretrained(str(out)); ok = (out / "model.onnx").exists()
    note(f"optimum 변환 {'성공' if ok else '파일 없음'}")
except Exception:
    note("optimum 변환 실패: " + traceback.format_exc()[-1500:])
if not ok:
    import torch
    hf.eval()
    enc = tok(["피부 재생 크림", "촉촉한 보습 로션입니다"], padding=True, return_tensors="pt")
    torch.onnx.export(hf, (enc["input_ids"], enc["attention_mask"]), str(out / "model.onnx"),
                      input_names=["input_ids", "attention_mask"], output_names=["last_hidden_state"],
                      dynamic_axes={"input_ids": {0: "b", 1: "s"}, "attention_mask": {0: "b", 1: "s"}, "last_hidden_state": {0: "b", 1: "s"}},
                      opset_version=14, do_constant_folding=True)
    note("torch.onnx 직접 변환 완료")
hf.config.save_pretrained(out)
from onnxruntime.quantization import quantize_dynamic, QuantType
quantize_dynamic(str(out / "model.onnx"), str(out / "model_quantized.onnx"), weight_type=QuantType.QInt8, per_channel=True)
# 변환이 맞는지: 원래(파이토치) 임베딩과 ONNX 임베딩 비교
import numpy as np, onnxruntime as ort
texts = ["피부 재생 크림", "아침에 마시는 따뜻한 차", "면역력 강화에 좋아요"]
ref = st.encode(texts, normalize_embeddings=True)
s = ort.InferenceSession(str(out / "model_quantized.onnx"), providers=["CPUExecutionProvider"])
names = {i.name for i in s.get_inputs()}
e = tok(texts, padding=True, return_tensors="np")
feed = {"input_ids": e["input_ids"].astype(np.int64), "attention_mask": e["attention_mask"].astype(np.int64)}
if "token_type_ids" in names: feed["token_type_ids"] = np.zeros_like(feed["input_ids"])
h = s.run(None, feed)[0]; mm = feed["attention_mask"][..., None]
v = (h * mm).sum(1) / mm.sum(1); v /= np.linalg.norm(v, axis=1, keepdims=True)
note(f"변환 확인: 원래 모델과 8비트 ONNX 임베딩 코사인 {[round(float(x), 4) for x in (ref * v).sum(1)]}")

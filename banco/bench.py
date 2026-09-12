import glob, time, os, numpy as np, onnxruntime as ort

models = sorted(glob.glob('${KINELAB_BENCH_DIR:-./banco/}models/**/end2end.onnx', recursive=True))
def label(p):
    for k in ['rtmpose-s','rtmpose-m','rtmpose-x','rtmw-dw-x-l']:
        if k in p: return k + (' 384x288' if '384x288' in p else ' 256x192')
    return p

for m in models:
    for prov in ['CPUExecutionProvider','CoreMLExecutionProvider']:
        try:
            so = ort.SessionOptions()
            so.log_severity_level = 3
            t0=time.time()
            s = ort.InferenceSession(m, so, providers=[prov])
            load = time.time()-t0
            i = s.get_inputs()[0]
            shape = [1 if (not isinstance(d,int) or d<=0) else d for d in i.shape]
            x = (np.random.rand(*shape)*255).astype(np.float32)
            name = i.name
            for _ in range(10): s.run(None, {name:x})
            ts=[]
            for _ in range(50):
                t=time.perf_counter(); s.run(None,{name:x}); ts.append((time.perf_counter()-t)*1000)
            ts=np.array(ts)
            print(f"{label(m):24s} {prov:26s} shape={shape} mean={ts.mean():7.2f}ms p50={np.median(ts):7.2f} p95={np.percentile(ts,95):7.2f} load={load:.1f}s used={s.get_providers()}", flush=True)
        except Exception as e:
            print(f"{label(m):24s} {prov:26s} ERROR {type(e).__name__}: {str(e)[:160]}", flush=True)

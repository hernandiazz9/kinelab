#!/bin/bash
# Uso: ./fps_truth.sh clip.mov
f="$1"
echo "--- campos declarados (pueden mentir) ---"
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,duration,time_base \
  -of default=noprint_wrappers=1 "$f"
echo "--- verdad: frames decodificados y deltas de PTS ---"
ffprobe -v error -select_streams v:0 -show_entries frame=pts_time -of csv=p=0 "$f" \
| awk -F, 'NF&&$1!=""{t[n++]=$1} END{
  if(n<2){print "frames="n; exit}
  for(i=1;i<n;i++){d=t[i]-t[i-1]; s+=d; if(d<mn||i==1)mn=d; if(d>mx)mx=d; h[sprintf("%.5f",d)]++}
  printf "frames=%d  span=%.4f s  delta_medio=%.6f s (%.2f fps)\n", n, t[n-1]-t[0], s/(n-1), (n-1)/(t[n-1]-t[0]);
  printf "delta_min=%.6f (%.1f fps)  delta_max=%.6f (%.1f fps)\n", mn, 1/mn, mx, 1/mx;
  print "histograma de deltas (top 5):";
  c=0; for(k in h){printf "  %s s  x%d\n", k, h[k]; if(++c>=5) break}
}'

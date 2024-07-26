; return detector (e.g. 'd1' or 'fhs') from a filename (w/o dir)
function detector_extract, filename, fnc=fnc
	case fnc of
	'ASC': return, strmid(filename,0,3) ; ASC file-name convention
	else: return, strmid(filename,10,1) ; MST file-name convention
	endcase
end

; return iteration (e.g. '5' or '001') from a filename (w/o dir)
function iteration_extract, filename, fnc=fnc
	case fnc of
	'ASC': return, strmid(filename,11,3) ; ASC file-name convention
	else: return, strmid(filename,12,strpos(filename,'pha')-13) ; MST file-name convention
	endcase
end

;+
; NAME:
;    bnd_view.pro
;
; NOTES:
;    1. !path=!path+":/home/rpete/local/src/pro/pha_tools" (my IDL routines for
;       pha files)
;
; CALLING SEQUENCE:
;    bnd_view, [dir], runid=runid [, its=its, fx=fx, sx=sx, fy=fy, sy=sy, $
;              fr=fr, sr=sr, psfile=psfile, sumdir=sumdir]
;
; REQUIRED INPUTS:
;    RUNID    = string runid (e.g., runid='114354')
;
; OPTIONAL INPUTS:
;    ITS      = Integer array of iterations to sum over (e.g. ITS=[0,2,3,4,10]).
;               Defaults to all available iterations.
;
;    BGDIR    = Directory containing background PHA files. The files should
;               be named for their respective detectors, e.g., "fpc_5.pha"
;
;    DIR      = Directory housing PHA files for BND's of the runid being used.
;               Defaults to current directory.
;
;    SR       = Region of interest for SSD detectors, in form of two element
;               integer vector (e.g., SR=[150,250]). Fluxes are calculated
;               based on the counts in this range of the ssd. Defaults
;               to entire region.
;
;    FR       = Same as SR, but for the FPC detectors.
;
;    S[X,Y]   = XRANGE and YRANGE for the SSD detector plots.
;
;    F[X,Y]   = XRANGE and YRANGE for the FPC detector plots.
;
;    PSFILE   = Postscript filename to write plot to.
;
;    SUMDIR   = If you wish to have output PHA files written of the sum of
;               all iterations used, set SUMDIR to the name of the directory
;               in which the output sums will go.
;
; REVISION HISTORY:
;    Created April, 1997 by Pete Ratzlaff <pratzlaff@cfa.harvard.edu> based
;    on previous work (RUN_PLOTTER.PRO, the interactive version).
;-
pro bnd_view, dir, runid=runid, its=its,  _extra=extra,  $
	fx=fx, fy=fy, $
	sx=sx, sy=sy, $
	fr=fr, sr=sr, $
	psfile=psfile, $
	sumdir=sumdir, bgdir=bgdir
	if not keyword_set(runid) then begin
		print,'RUNID keyword must be set...returning'
		retall
	endif

	; useful array later
	all_detectors=['fpc_ht','','fpc_hb','fpc_5','fpc_hs','ssd_5','fpc_hn']
	
	; plot to Postscript file, if requested
	if keyword_set(psfile) then begin
		old_device=!d.name
		set_plot,'PS'
		device,filename=psfile,/landscape
	endif

	; do I have to do everything around here?!
	if n_params() lt 1 then begin
		spawn,'pwd',dir,/noshell & dir=dir(0)
	endif
	dir=dir+'/'

;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; get list of all filenames
;
	print,'Finding all runid '+runid+' files in '+dir+'...'
	files=findfile(dir+'*'+runid+'*',count=cnt)
	if cnt eq 0 then begin
		print,'No runid '+runid+' files found in '+dir+'...returning'
		retall
	endif
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; a lot of filenames begin with the string 'sum'
;
	nf=['']
	for i=0l,n_elements(files)-1 do begin
		fdecomp,files(i),j1,j2,name1
		if strmid(name1,0,3) ne 'sum' then nf=[nf,files(i)]
	endfor
	if n_elements(nf) eq 1 then begin
		print,'No runid '+runid+' files found in '+dir+'...returning'
		retall
	endif else files=nf(1:n_elements(nf)-1)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; extract filename extensions
;
	exts=strarr(n_elements(files))
	for i=0,n_elements(files)-1 do begin
		files(i)=strmid(files(i),strlen(dir),100)
		fdecomp,files(i),j1,j2,name1,ext
		if ext eq 'gz' then fdecomp,name1,j1,j2,name2,ext
		exts(i)=ext
	endfor

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; extract 'pha' files, decide which filename convention is used
;
	index=where(exts eq 'pha',cnt) 
	if cnt gt 0 then $
		pha_files=files(index) $
	else begin
		print,'No BND files for runid '+runid+' found in '+dir+'...returning'
		retall
	endelse
	case strmid(pha_files(0),0,3) of
		'acq': fnc='MST'
		else: fnc='ASC'
	endcase

;;;;;;;;;;;;;;;;;;;;;
; extract 'sum' files
;
	index=where(exts eq 'sum',cnt) 
	if cnt gt 0 then begin
		sum_files=files(index) 
		sum_files=sum_files(sort(sum_files))
	endif

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; get list of all iterations, check against keyword inputs
	print,'Checking for valid iterations...'
	all_iteration=strarr(n_elements(pha_files))
	for i=0,n_elements(pha_files)-1 do all_iteration(i)=iteration_extract(pha_files(i),fnc=fnc)
	all_iteration=fix(all_iteration)
	iteration=all_iteration(sort(all_iteration)) & iteration=iteration(uniq(iteration))
	if not keyword_set(its) then its=iteration $
	; check input iterations if necessary
	else begin 
		new_its=0
		for i=0,n_elements(its)-1 do begin
			index=where(iteration eq its(i),cnt)
			if cnt eq 0 then $
				print,'Iteration '+strtrim(string(its(i)),2)+ $
					' not available, skipping' $
			else new_its=[new_its,iteration(index(0))]
		endfor
		if n_elements(new_its) eq 1 then begin
			print,'No iterations found. Quitting'
			retall
		end else its=new_its(1:n_elements(new_its)-1)
	endelse
	its=its(sort(its))
	its_str=strtrim(string(its),2)
	if fnc eq 'ASC' then begin
		index=where(its_str lt 10,cnt)
		if cnt gt 0 then its_str(index)='00'+its_str(index)
		index=where(its_str lt 100 and its_str ge 10,cnt)
		if cnt gt 0 then its_str(index)='0'+its_str(index)
	endif
	index=0
	for i=0,n_elements(its)-1 do $
		index=[index,where(all_iteration eq its(i))]
	index=index(1:n_elements(index)-1)
	pha_files=pha_files(index)
	; the SUMDIR keyword makes new pha files which can throw us for a loop
	pha_files=pha_files(where(strpos(pha_files,'-',10) eq -1,tc))
	; now 'its' and 'its_str' are all we care about

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; get list of detectors used and corresponding 'sum' files
;
	case fnc of
		'MST': detector=strmid(pha_files,9,2)
		'ASC': detector=strmid(pha_files,0,3)
	endcase
	detector=detector(sort(detector))
	detector=detector(uniq(detector))
	if n_elements(sum_files) eq n_elements(detector) then $
		sum_exist=1 $
	else begin
		print,'Not all sum files exist. No fluxes for you!'
		sum_exist=0
	endelse

; construct 2-d file array
;
	file_array=strarr(n_elements(detector),n_elements(its))
	for i=0,n_elements(detector)-1 do begin
		case fnc of 
			'MST': file_array(i,*)=pha_files(where(strmid(pha_files,9,2) eq detector(i)))
			'ASC': file_array(i,*)=pha_files(where(strmid(pha_files,0,3) eq detector(i)))
		endcase
	endfor

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; misc parameters for instrument configuration
;
	detector_area=[32.26,0.0] ; fpc & ssd areas, respectively
	if sum_exist then begin
		date=get_filetime(dir+sum_files(0))
		source=get_source(dir+sum_files(0))
		energy=get_energy(dir+sum_files(0))
		trw_id=get_trw_id(dir+sum_files(0))

		; order of distances is...
		;                          1.fpc_ht
		;                          2. focal plane
		;                          3. fpc_hb
		;                          4. fpc_5
		;                          5. fpc_hs
		;                          6. ssd_5
		;                          7. fpc_hn
		case strmid(source,0,1) of
			'H': begin ; HIREFS
				d1=1721.0281d ; source to BND-H
				d2=122.3021d ; source to BND-5
			end
			'D': begin ; DCM
				d1=1724.3321d
				d2=125.5521d
			end
			'E': begin ; EIPS
				d1=1721.405d
				d2=122.625d
			end
			'P': begin ; PENNING
				d1=1722.9363d
				d2=124.1563d
			end
		endcase
		
		d3=11.2917d ; HRMA to BND-H
		distances=[ d1, d1+d3+32.808d, d1, d2, d1, d2, d1]
		hrma_dist=d1+d3
		

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; get quantum efficiencies for energy at hand
;
		read_fpc_qe, fpc_kev, fpc_qe
		read_ssd_qe, ssd_kev, ssd_qe
		index=where(abs(energy-fpc_kev) eq min(abs(energy-fpc_kev)))
		fpc_qe=fpc_qe(index(0))
		index=where(abs(energy-ssd_kev) eq min(abs(energy-ssd_kev)))
		ssd_qe=ssd_qe(index(0))

	; sum files missing
	end else begin
		distances=[0.,0.,0.,0.,0.,0.,0.]
		energy='0.0'
		source='unknown'
		trw_id='unknown'
		date=get_filetime(dir+file_array(0,0))
	endelse

	erase
	!p.multi=[0,2,4]
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; for each detector, plot the data
;
	for i=0,n_elements(detector)-1 do begin
		focal_plane=0
		temp_livetime=0.0
		livetime=0.0
		data=lonarr(n_channels(dir+file_array(i,0)))
		this_detector=get_detector(dir+file_array(i,0))
		if keyword_set(bgdir) then begin
			bg_file=findfile(bgdir+'/'+this_detector+'.pha')
			if strlen(bg_file) eq 0 then begin
				print,'Background file for '+this_detector+' not found! Returning'
				retall
			endif
			bg_file=bg_file(0)
		endif
		print,'Reading data for detector '+this_detector
		; sum the iterations
		temp_livetime=0.0
		for j=0,n_elements(its)-1 do begin
			data=data+read_pha_data(dir+file_array(i,j),temp_livetime)
			livetime=livetime+temp_livetime
		endfor
	
		index=where(this_detector eq all_detectors, cnt)
		if cnt eq 0 then begin
			if this_detector ne 'fpc_x1' $
				and this_detector ne 'fpc_x2' $
				and this_detector ne 'ssd_x' then $
			message,'Cannot find a place for plot with detector '+this_detector $
			else begin
				focal_plane=1
				!p.multi=[7,2,4]
				dist=0.0
			endelse
		endif else begin
			!p.multi=[8-index(0),2,4]
			dist=distances(index(0))
		endelse
		
		err=sqrt(data)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; the following billions lines of code are tedious
		; find some reasonable plot ranges, get roi
		case strmid(this_detector,0,3) of
		'fpc': begin 
			area=detector_area(0)
			if sum_exist then det_qe=fpc_qe ; otherwise, we don't need QE

			; ROI
			if not keyword_set(fr) then roi=[0,n_elements(data)-1] $
			else roi=fr

			; user selected no ranges for plot
			if not keyword_set(fy) and not keyword_set(fx) then begin
				xrange=[0,0] & yrange=[0,0]
			endif

			; user selected both plot ranges
			if keyword_set(fx) and keyword_set(fy) then begin
				xrange=fx & yrange=fy
			endif

			; user selected Yrange
			if keyword_set(fy) and not keyword_set(fx) then begin
				yrange=fy
				xrange=[0,0]
			endif

			; user selected Xrange
			if keyword_set(fx) and not keyword_set(fy) then begin
				yrange=[0,0]
				xrange=fx
			endif
		end
		'ssd': begin 
			area=detector_area(1)
			if sum_exist then det_qe=ssd_qe ; otherwise, we don't need QE

			; ROI
			if not keyword_set(sr) then roi=[0,n_elements(data)-1] $
			else roi=sr

			; user selected no ranges for plot
			if not keyword_set(sy) and not keyword_set(sx) then begin
				xrange=[0,0] & yrange=[0,0]
			endif

			; user selected both plot ranges
			if keyword_set(sx) and keyword_set(sy) then begin
				xrange=sx & yrange=sy
			endif

			; user selected Yrange
			if keyword_set(sy) and not keyword_set(sx) then begin
				yrange=sy
				xrange=[0,0]
			endif

			; user selected Xrange
			if keyword_set(sx) and not keyword_set(sy) then begin
				yrange=[0,0]
				xrange=sx
			endif
		end
		endcase

		; check for silly inputs
		if min(xrange) lt 0 or max(xrange) ge n_elements(data) then $
			xrange=[0,0]

; end of tedious code
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

		roi_sum=long(total(data(roi(0):roi(1))))
		xtitle='ROI=['+strtrim(string(fix(roi(0))),2)+','+strtrim(string(fix(roi(1))),2)+'] Sum='+strtrim(string(long(total(data(roi(0):roi(1))))),2)+'C'
		if area gt 0.0 and energy gt 0.0 and not focal_plane then begin
			flux=roi_sum/livetime/det_qe/area*(dist/hrma_dist)^2
			xtitle=xtitle+', HRMA flux='+strn(flux,f='(e8.2)')+textoidl("C s^{-1} cm^{-2}")
		endif
		if focal_plane then xtitle=xtitle+', Rate='+strn(roi_sum/livetime)+textoidl("C s^{-1}")
		
		title=this_detector+'('+detector(i)+')'+$
			', runid='+runid+', livetime='+strn(livetime)+'s'
		;case fnc of
			;'ASC': title=this_detector+$
			;', runid='+runid+', livetime='+strn(livetime)+'s'
		;endcase
		if keyword_set(psfile) then charsize=1.2 else charsize=2.0
		if yrange(0)^2+yrange(1)^2 ne 0 then plot_data=data/livetime $
		else plot_data=(data>.8)/livetime
		plot, plot_data, _extra=extra, title=title, $
			chars=charsize, yrange=yrange, $
			xtitle=xtitle,ytitle='Count Rate', $
			/ylog, xrange=xrange, ysty=1, xstyle=1
		oplot,[roi(0),roi(0)],[1e9,1e-9]
		oplot,[roi(1),roi(1)],[1e9,1e-9]
		oploterr,indgen(n_elements(data)),data/livetime,err/livetime,0
;
; end of plotting section
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; write new PHA file if requested
;
		if keyword_set(sumdir) then begin

			; '#iterations:' field in new PHA file
			its_string_all=''
			for z=0,n_elements(its_str)-1 do $
				its_string_all=its_string_all+its_str(z)+' '

			; filename for summed output
			case fnc of
			'MST': newfile='acq'+runid+detector(i)+'i'+its_str(0)+$
				'-'+its_str(n_elements(its_str)-1)+'.pha'
			'ASC': newfile=detector(i)+'_'+runid+'i'+its_str(0)+$
				'-'+its_str(n_elements(its_str)-1)+'.pha'
			endcase

			; now do the writing
			openw,newunit,sumdir+'/'+newfile,/get_lun
			printf,newunit,'#filename:	'+newfile
			printf,newunit,'#fileCreationDate:	'+systime()
			printf,newunit,'#irigStartTime:	'+get_irigtime(dir+file_array(i,0))
			printf,newunit,'#uniqueId:	'+runid
			printf,newunit,'#channels:	'+strn(n_elements(data))
			printf,newunit,'#liveTime_sec:	'+strn(livetime)
			printf,newunit,'#iterations_summed:	'+its_string_all
			printf,newunit,this_detector
			printf,newunit,'------'
			; the following business is for a tidy-looking PHA file
			for z=0,n_elements(data)-1 do begin
				dummy=strn(data(z))
				printf,newunit,dummy,format='(A'+strn(strlen(dummy))+')'
			endfor
			close,newunit & free_lun,newunit
		endif
;
; done with new PHA file
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
	endfor

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; put some info on the plot
;

	; TRW_ID
	xyouts,.55,.24,'TRW_ID:',/norm,chars=charsize/2.0
	xyouts,.64,.24,trw_id,/norm,chars=charsize/2.0

	; energy
	energy_str=strtrim(string(energy),2)
	while strmid(energy_str,strlen(energy_str)-1,1) eq '0' do $
		energy_str=strmid(energy_str,0,strlen(energy_str)-1)
	xyouts,.55,.22,'Energy:',/norm,chars=charsize/2.0
	if sum_exist then $
		xyouts,.64,.22,energy_str+' kev',/norm,chars=charsize/2.0 $
	else $
		xyouts,.64,.22,'unknown',/norm,chars=charsize/2.0

	; source
	xyouts,.55,.20,'Source:',/norm,chars=charsize/2.0
	xyouts,.64,.20,source,/norm,chars=charsize/2.0

	; date
	xyouts,.55,.18,'Date:',/norm,chars=charsize/2.0
	xyouts,.64,.18,date,/norm,chars=charsize/2.0

	; directory
	xyouts,.55,.16,'Directory:',/norm,chars=charsize/2.0
	xyouts,.64,.16,dir,/norm,chars=charsize/2.0

	; list of iterations
	xyouts,.55,.14,'Iterations: ',/norm,chars=charsize/2.0
	label=''
	y_coord=.14
	x_coord=.68
	counter=0
	for i=0,n_elements(its)-1 do begin
		xyouts,x_coord,y_coord,strtrim(string(its(i)),2),/norm,$
			align=1.0,chars=charsize/2.0
		counter=counter+1
		if counter eq 7 then begin
			counter=0
			x_coord=.68
			y_coord=y_coord-.02
		end else x_coord=x_coord+0.05
	endfor
;
; done putting info on plot
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

; close Postscript, if necessary
	if keyword_set(psfile) then begin
		device,/close
		set_plot,old_device
	endif
end

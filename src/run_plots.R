# run_plots.R — v15-compatible age-model and proxy plotting for SISAL workbooks.
#
# Usage (from the datasteward-AutoQC/ folder):
#   Rscript run_plots.R SISAL_workbook_v15_SiteName_EntityName.xlsx
#
# Input:  Filled_SISAL_Workbook_v15/<filename>
# Output: Output/QC_agemodel_hiatus_<SiteName>_<EntityName>.pdf
#
# v15 compatibility fixes applied here (two columns dropped vs v14):
#   modern_reference — injected as 'BP (1950)'; all v15 ages are already BP(1950)
#   depth_ref        — inferred per entity from sign of mean(diff(interp_age))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0) {
  stop("Usage: Rscript run_plots.R <SISAL_workbook_v15_filename.xlsx>")
}
xls <- args[1]

# Paths — env vars take priority (web mode); fall back to local defaults
input_dir_env  <- Sys.getenv("SISAL_INPUT_DIR",  unset = "")
output_dir_env <- Sys.getenv("SISAL_OUTPUT_DIR", unset = "")
input_file <- if (nchar(input_dir_env)  > 0) file.path(input_dir_env,  xls) else file.path("Filled_SISAL_Workbook_v15", xls)
output_dir <- if (nchar(output_dir_env) > 0) output_dir_env              else "Output"
dir.create(output_dir, showWarnings = FALSE)

# Source the plotting library (Age_corrected2reference lives here)
args_all <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("--file=", args_all, value = TRUE)

if (length(file_arg) > 0) {
  script_dir <- dirname(sub("--file=", "", file_arg[1]))
  source(file.path(script_dir, "plot_agemodels_hiatus.R"))
} else {
  source("plot_agemodels_hiatus.R")
}

library(openxlsx)
library(ggplot2)

# Helper: infer depth_ref from data (mirrors Python auto-detection)
infer_depth_ref <- function(entity_name, sample_tb) {
  sub <- sample_tb[sample_tb$entity_name == entity_name & is.na(sample_tb$hiatus), ]
  sub <- sub[!is.na(sub$depth_sample) & !is.na(sub$interp_age), ]
  sub <- sub[order(as.numeric(sub$depth_sample)), ]
  if (nrow(sub) < 2) return('from top')
  m <- mean(diff(as.numeric(sub$interp_age)), na.rm = TRUE)
  if (m > 0) 'from top' else if (m < 0) 'from base' else 'from top'
}

# Override plot_agemodels_hiatus with v15-compatible version
plot_agemodels_hiatus <- function(input_file, output_dir) {

  site_tb          <- read.xlsx(input_file, sheet = 'Site metadata',       startRow = 2)
  entity_tb        <- read.xlsx(input_file, sheet = 'Entity metadata',     startRow = 2)
  sample_tb        <- read.xlsx(input_file, sheet = 'Sample data',         startRow = 2)
  dating_tb        <- read.xlsx(input_file, sheet = 'Dating information',  startRow = 2)
  dating_lamina_tb <- read.xlsx(input_file, sheet = 'Lamina age vs depth', startRow = 2)

  # v15 fix 1: inject modern_reference so Age_corrected2reference works.
  # All v15 ages are BP(1950); converting to b2k adds 50 years.
  if (nrow(sample_tb) > 0)        sample_tb$modern_reference        <- 'BP (1950)'
  if (nrow(dating_tb) > 0)        dating_tb$modern_reference        <- 'BP (1950)'
  if (nrow(dating_lamina_tb) > 0) dating_lamina_tb$modern_reference <- 'BP (1950)'

  # v15 fix 2: infer depth_ref per entity
  entity_tb$depth_ref <- sapply(entity_tb$entity_name, infer_depth_ref, sample_tb = sample_tb)

  if (any(c(site_tb == "NULL", entity_tb == "NULL", sample_tb == "NULL",
            dating_tb == "NULL", dating_lamina_tb == "NULL"), na.rm = TRUE)) {
    warning("NULL values found. Terminating plotting script.")
    stop()
  }

  for (col in c('depth_sample', 'interp_age')) {
    if (class(sample_tb[[col]]) != 'numeric') {
      writeLines(paste('Converting', col, 'in Sample data to numeric'))
      sample_tb[[col]] <- as.numeric(sample_tb[[col]])
    }
  }
  for (col in c('depth_dating', 'corr_age', 'corr_age_uncert_neg', 'corr_age_uncert_pos')) {
    if (class(dating_tb[[col]]) != 'numeric') {
      writeLines(paste('Converting', col, 'in Dating information to numeric'))
      dating_tb[[col]] <- as.numeric(dating_tb[[col]])
    }
  }
  if (nrow(dating_lamina_tb) > 0) {
    for (col in c('depth_lam', 'lam_age')) {
      if (class(dating_lamina_tb[[col]]) != 'numeric') {
        writeLines(paste('Converting', col, 'in Lamina age vs depth to numeric'))
        dating_lamina_tb[[col]] <- as.numeric(dating_lamina_tb[[col]])
      }
    }
  }

  entity_name_list <- unique(entity_tb$entity_name)
  entity_name_list <- entity_name_list[!is.na(entity_name_list)]
  grp_ctr <- 1
  p_temp <- ggplot() + theme_bw() +
    theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank())

  for (i in entity_name_list) {
    writeLines(paste0("Processing entity: ", i))
    entity_name              <- i
    speleothem_type          <- entity_tb$speleothem_type[entity_tb$entity_name == i]
    contact_name             <- entity_tb$contact[entity_tb$entity_name == i]
    depth_ref                <- entity_tb$depth_ref[entity_tb$entity_name == i]
    sample_from_entity       <- subset(sample_tb,        entity_name == i)
    dating_for_entity        <- subset(dating_tb,        entity_name == i)
    dating_lamina_for_entity <- subset(dating_lamina_tb, entity_name == i)

    sample_from_entity$grp <- NA
    for (k in 1:nrow(sample_from_entity)) {
      if (is.na(sample_from_entity[k, 'gap']) & is.na(sample_from_entity[k, 'hiatus'])) {
        sample_from_entity$grp[k] <- toString(grp_ctr)
      } else {
        grp_ctr <- grp_ctr + 1
      }
    }
    sample_entity_hiatus <- subset(sample_from_entity, hiatus == "H")
    sample_from_entity   <- subset(sample_from_entity, is.na(gap))
    sample_from_entity   <- subset(sample_from_entity, is.na(hiatus))

    dating_present <- FALSE
    sample_present <- FALSE

    if (nrow(dating_for_entity) > 1) {
      dating_present <- TRUE
      dating_for_entity_NA    <- dating_for_entity[is.na(dating_for_entity$date_used), ]
      dating_for_entity_NotNo <- dating_for_entity[!is.na(dating_for_entity$date_used) &
                                                      dating_for_entity$date_used != 'no', ]
      dating_for_entity <- rbind(dating_for_entity_NA, dating_for_entity_NotNo)
      dating_for_entity <- subset(dating_for_entity,
                                  date_type != 'Event; hiatus' &
                                    date_type != 'Event; gap (composite record)')
      dating_for_entity <- Age_corrected2reference(dating_for_entity,
                                                   old_age_columns = 'corr_age', dating = TRUE)
      if (nrow(dating_lamina_for_entity) > 0) {
        dating_lamina_for_entity <- Age_corrected2reference(dating_lamina_for_entity,
                                                            old_age_columns = 'lam_age')
      }
    } else {
      writeLines(paste('  No dating information for', entity_name))
    }

    if (nrow(sample_from_entity) > 1) {
      sample_present <- TRUE
      if (length(sample_from_entity$interp_age[!is.na(sample_from_entity$interp_age)]) > 0) {
        sample_from_entity <- Age_corrected2reference(sample_from_entity, dating_table = dating_tb)
      } else {
        sample_from_entity$Age_corrected2reference <- NA
      }
    } else {
      writeLines(paste('  No sample data for', entity_name))
    }

    make_blank <- function(msg) p_temp + annotate("text", x = 4, y = 25, size = 8, label = msg)

    if (sample_present &&
        nrow(sample_from_entity[!is.na(sample_from_entity$Age_corrected2reference), ]) > 1) {

      if (dating_present &&
          nrow(dating_for_entity[!is.na(dating_for_entity$Age_corrected2reference), ]) > 1) {
        dating_for_entity$upper <- dating_for_entity$Age_corrected2reference +
          dating_for_entity$corr_age_uncert_pos
        dating_for_entity$lower <- dating_for_entity$Age_corrected2reference -
          dating_for_entity$corr_age_uncert_neg

        p <- ggplot() +
          geom_point(data = dating_for_entity,
                     aes(x = Age_corrected2reference / 1000, y = depth_dating)) +
          geom_errorbar(data = dating_for_entity,
                        aes(y = depth_dating, xmin = lower / 1000, xmax = upper / 1000),
                        orientation = 'y') +
          geom_path(data = sample_from_entity,
                    aes(x = Age_corrected2reference / 1000, y = depth_sample, group = grp)) +
          xlab('Age (ka b2k)') +
          ylab(paste('Distance', depth_ref, '(mm)')) +
          geom_hline(mapping = aes(
            yintercept = sample_entity_hiatus[['depth_sample']],
            colour = rep('hiatuses in workbook', length(sample_entity_hiatus[['depth_sample']]))),
            linetype = 'dotted', show.legend = TRUE) +
          scale_x_reverse() +
          ggtitle(paste0('Age model: ', entity_name, ' (', contact_name, ')')) +
          theme(legend.title = element_blank())

        if (depth_ref == 'from top') p <- p + scale_y_reverse()
        if (depth_ref == 'from base') {
          sample_from_entity <- sample_from_entity[rev(order(sample_from_entity$depth_sample)), ]
        } else {
          sample_from_entity <- sample_from_entity[order(sample_from_entity$depth_sample), ]
        }
        if (nrow(dating_lamina_for_entity) > 0) {
          p <- p +
            geom_point(data = dating_lamina_for_entity,
                       aes(x = Age_corrected2reference / 1000, y = depth_lam,
                           colour = 'lamina age vs depth')) +
            geom_path(data = sample_from_entity,
                      aes(x = Age_corrected2reference / 1000, y = depth_sample,
                          group = grp, colour = 'sample data')) +
            scale_colour_manual(values = c('red', 'blue', 'black'))
        }
      } else {
        p <- make_blank(paste0('Entity ', entity_name,
                               ': no valid dating information.\nAge model cannot be plotted.'))
      }

      a <- sample_from_entity[['depth_sample']]
      sample_midpoint <- a[-length(a)] + diff(a) / 2
      interp_age_diff <- diff(sample_from_entity[['Age_corrected2reference']])
      dt <- data.frame(depth = sample_midpoint, interp_age_diff = interp_age_diff)
      p1 <- ggplot() +
        geom_line(data = dt, aes(x = sample_midpoint, y = interp_age_diff)) +
        xlab(paste0('Sample depth midpoints ', depth_ref, ' (mm)')) +
        ylab('Age difference between consecutive samples (years)')
      if (nrow(sample_entity_hiatus) > 0) {
        p1 <- p1 + geom_vline(xintercept = sample_entity_hiatus[['depth_sample']],
                               linetype = 'dotted', colour = 'red')
      }

      make_proxy <- function(col, ylabel, title_prefix) {
        sub <- subset(sample_from_entity, !is.na(sample_from_entity[[col]]))
        if (nrow(sub) > 0) {
          ggplot() +
            geom_point(data = sub, aes(x = Age_corrected2reference / 1000, y = .data[[col]])) +
            geom_path(data  = sub, aes(x = Age_corrected2reference / 1000, y = .data[[col]],
                                       group = grp)) +
            xlab('Age (ka b2k)') + ylab(ylabel) + scale_x_reverse() +
            ggtitle(paste0(title_prefix, entity_name, ' (', contact_name, ')')) +
            theme(legend.title = element_blank())
        } else {
          make_blank(paste0('Entity ', entity_name, ': no ', ylabel, ' data.'))
        }
      }

      p2 <- make_proxy('d18O_measurement',        'd18O (permil)',          'd18O vs age -')
      p3 <- make_proxy('d13C_measurement',        'd13C (permil)',          'd13C vs age -')
      p4 <- make_proxy('Sr_Ca_measurement',       'Sr/Ca (mmol/mol)',       'Sr/Ca vs age -')
      p5 <- make_proxy('Mg_Ca_measurement',       'Mg/Ca (mmol/mol)',       'Mg/Ca vs age -')
      p6 <- make_proxy('Ba_Ca_measurement',       'Ba/Ca (mmol/mol)',       'Ba/Ca vs age -')
      p7 <- make_proxy('U_Ca_measurement',        'U/Ca (mmol/mol)',        'U/Ca vs age -')
      p8 <- make_proxy('P_Ca_measurement',        'P/Ca (mmol/mol)',        'P/Ca vs age -')
      p9 <- make_proxy('Sr_isotopes_measurement', 'Sr isotopes (mmol/mol)', 'Sr isotopes vs age -')

    } else {
      msg_sfx <- if (sample_present) 'with valid dates' else ''
      p  <- make_blank(paste0('Entity ', entity_name, ': no sample data ', msg_sfx, '.'))
      p1 <- make_blank(paste0('Entity ', entity_name, ': no sample data — hiatus plot unavailable.'))
      p2 <- make_blank(paste0('Entity ', entity_name, ': no d18O data.'))
      p3 <- make_blank(paste0('Entity ', entity_name, ': no d13C data.'))
      p4 <- make_blank(paste0('Entity ', entity_name, ': no Sr/Ca data.'))
      p5 <- make_blank(paste0('Entity ', entity_name, ': no Mg/Ca data.'))
      p6 <- make_blank(paste0('Entity ', entity_name, ': no Ba/Ca data.'))
      p7 <- make_blank(paste0('Entity ', entity_name, ': no U/Ca data.'))
      p8 <- make_blank(paste0('Entity ', entity_name, ': no P/Ca data.'))
      p9 <- make_blank(paste0('Entity ', entity_name, ': no Sr isotopes data.'))
    }

    site_name_short <- unlist(strsplit(site_tb$site_name, " ", fixed = TRUE))[1]
    pdf_file <- file.path(output_dir,
                          paste0('QC_agemodel_hiatus_', site_name_short, '_', entity_name, '.pdf'))
    pdf(pdf_file, 10, 8)
    print(p); print(p1); print(p2); print(p3); print(p4)
    print(p5); print(p6); print(p7); print(p8); print(p9)
    dev.off()
    writeLines(paste0("  -> saved: ", pdf_file))

    # Individual PNG exports for web interface
    plot_list <- list(
      list(p = p,  name = "01_agemodel"),
      list(p = p1, name = "02_age_diff"),
      list(p = p2, name = "03_d18O"),
      list(p = p3, name = "04_d13C"),
      list(p = p4, name = "05_Sr_Ca"),
      list(p = p5, name = "06_Mg_Ca"),
      list(p = p6, name = "07_Ba_Ca"),
      list(p = p7, name = "08_U_Ca"),
      list(p = p8, name = "09_P_Ca"),
      list(p = p9, name = "10_Sr_isotopes")
    )
    for (pl in plot_list) {
      png_file <- file.path(output_dir,
                            paste0("plot_", entity_name, "_", pl$name, ".png"))
      png(png_file, width = 1000, height = 800, res = 100)
      print(pl$p)
      dev.off()
      writeLines(paste0("  -> saved: ", png_file))
    }
  }
}

# ---- run --------------------------------------------------------------------
plot_agemodels_hiatus(input_file, output_dir)
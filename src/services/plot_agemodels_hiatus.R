# plot_agemodels_hiatus_v12.R ---------------------------------------------------####
# 
# This script creates at least two plots, and up to four plots:
#     1. Age model plot, which is essentially, the samples, overlaid by the dating 
#     information (and lamina age vs depth if available). Hiatuses are marked with a
#     dashed line.
#     2. Interp_age differences between consecutive depths and their respective depths. 
#     Hiatuses in the workbook are marked with a red line. This plot is used to
#     identify where there are large jumps in interpolated ages which have not been
#     marked as a hiatus in the workbook. IF NEW HIATUSES ARE ADDED TO THE WORKBOOK,
#     PLEASE RUN THESE THROUGH THE PYTHON CHECKS AGAIN, AND MAKE SURE TO ADD THIS TO 
#     BOTH THE "Dating information" table and the "Sample data" table
#     3. d18O vs time (if both d18O and interp_age are present)
#     4. d13C vs time (if both d13C and interp_age are present)
#
# The script requires:
#     1. path to excel workbook file version 11 (input_file, line 30)
#
# The script outputs:
#     1. a pdf file for each entity in the workbook with the plots described above
#
# Edits
# 
# 17th February 2021
#     - Changed name to plot_age_models_hiatus.R to allow for a better version control. This version corresponds to v12,
# which is the one used in the SISALv2 (ID 256) workbooks

# 19th December 2018
#     - updated so that the the d18O and d13C vs time plots are generated where possible.
#
# 16th October 2018
#     - updated so that the depth and the age columns when read are always numeric
#
# 17th September 2018
#     - updated so that hiatus plot ages between consecutive plots are not upside down when modern reference = 'CE/BCE'
#
# 3rd January 2019
#     - updated so that the d18O and d13C plots are correct (they were plotting the same time series) L275/276
#

# rm(list=ls())

# setwd ("[ENTER WD PATH]") #UoR desktop


# path to excel workbook file version 14 ----------------------------------------####
# input_file <- 'SISAL_workbook_v11_NAME.xlsx'

# Install and load prerequisite packages ----------------------------------------####

if (!('openxlsx' %in% installed.packages())){ # Install these packages has it not been already installed
  install.packages('openxlsx')
}

if (!('ggplot2' %in% installed.packages())){
  install.packages('ggplot2')
}

# Load the library
library(openxlsx)
library(ggplot2)

# Define prerequisite functions -------------------------------------------------####
# Function to corrected Interp age, etc., to reference. 
Age_corrected2reference <- function(sample_table,
                                    reference_column_name = 'modern_reference', 
                                    standard_reference = 'b2k', 
                                    new_column_name = 'Age_corrected2reference',
                                    old_age_columns = 'interp_age',
                                    dating = FALSE,
                                    dating_table = dating_tb){
  # Corrects all ages to b2k for plotting age model
  #
  # Args:
  #   sample_table: dataframe, table with the column with ages to be corrected
  #   reference_column_name: character, name of column with the modern reference (default to 'modern_reference')
  #   standard_reference: character, currently only accepting 'b2k' (default to 'b2k')
  #   new_column_name: character, name of new age column after the ages have been corrected (default to 'Age_corrected2reference') 
  #   old_age_columns: character, name of age column to be corrected (default to 'interp_age')
  #   dating: boolean, whether or not the sample_table is the dating table
  #   dating_table: dataframe, table with the dating information where the year of chemistry can be found (this is default to dating_tb)
  #
  # Returns:
  #   sample_table with the a new column (new_column_name) containing ages (old_age_columns) corrected to b2k
  #
  table <- sample_table
  if (dim(table)[1] > 1){
    if (standard_reference == 'b2k'){
      # writeLines(paste('You picked', standard_reference, 'as reference'))
      table[table[reference_column_name] == 'b2k', new_column_name] <- table[table[reference_column_name] == 'b2k', old_age_columns]
      table[table[reference_column_name] == 'BP (1950)', new_column_name] <- table[table[reference_column_name] == 'BP (1950)', old_age_columns] + 50
      table[table[reference_column_name] == 'CE/BCE', new_column_name] <- 2000 - (table[table[reference_column_name] == 'CE/BCE', old_age_columns])
      if (dim(table[table[reference_column_name] == 'Year of chemistry',])[1] > 1){
        # create a list of entities with 'Year of chemistry'
        entity_ls = unique(table$entity_name[table[reference_column_name] == 'Year of chemistry'])
        # loop through each entity with Modern reference as 'Year of chemistry'
        for (j in entity_ls){
          if (dating == FALSE){
            chem_year = unique(dating_table$chem_year[dating_table$entity_name == j])
            chem_year <- sort(chem_year[!is.na(chem_year)])
            if (length(chem_year) < 1){
              writeLines(paste('No Year done in dating information table for entity name = ', j))
            } else if (length(chem_year) == 1){
              #perform conversion
              table[table[reference_column_name] == 'Year of chemistry' & table$entity_name == j, new_column_name] <- table[table[reference_column_name] == 'Year of chemistry' & table$entity_name == j, old_age_columns] + (2000 - chem_year[[1]])
            } else if (length(chem_year) > 1){
              writeLines(paste('There is more than reference year for this particular entity entity id = ', j))
              writeLines('The most recent year will be used')
              chem_year <- chem_year[length(chem_year)]
              table[table[reference_column_name] == 'Year of chemistry' & table$entity_name == j, new_column_name] <- table[table[reference_column_name] == 'Year of chemistry' & table$entity_name == j, old_age_columns] + (2000 - max(chem_year))
            }
          } else if (dating == TRUE){
            table[table[reference_column_name] == 'Year of chemistry' & table$entity_name == j, new_column_name] <- table[table[reference_column_name] == 'Year of chemistry' & table$entity_name == j, old_age_columns] + (2000 - table$chem_year[table[reference_column_name] == 'Year of chemistry' & table$entity_name == j])
          }
        }
      }
    }
  } else {
    writeLines('Input table has no data in it. Returning empty table')
  }
  return(table)
}

plot_agemodels_hiatus <- function(pth, xls) {
  input_file <- paste0(pth, "/", xls)
  
  # Read in the tables ------------------------------------------------------------####
  # Read in the Entity table, sample table, dating table and lamina age vs depth table
  site_tb          <- read.xlsx(input_file, sheet = 'Site metadata',       startRow = 2)
  entity_tb        <- read.xlsx(input_file, sheet = 'Entity metadata',     startRow = 2)
  sample_tb        <- read.xlsx(input_file, sheet = 'Sample data',         startRow = 2)
  dating_tb        <- read.xlsx(input_file, sheet = 'Dating information',  startRow = 2)
  dating_lamina_tb <- read.xlsx(input_file, sheet = 'Lamina age vs depth', startRow = 2)
  
  # If NULL values detected stop
  if (any(c(site_tb =="NULL", entity_tb =="NULL", sample_tb =="NULL", dating_tb =="NULL", dating_lamina_tb =="NULL"), na.rm = T)) {
    warning("There are NULL values. Terminating plotting script.")
    stop()
  }
  
  # Convert particular columns to numeric -----------------------------------------####
  for (i in c('depth_sample', 'interp_age')){
    if (class(sample_tb[[i]]) != 'numeric'){
      writeLines(paste('Somehow ', i, ' in Sample data table is not read as numeric. This rarely occurs (if it truly is not numeric, it should have been caught by the python checks first). This column will be coverted to numeric where possible. Please see that there is no warning and please mention this in the email when sending the workbook', sep = ''))
      sample_tb[[i]] <- as.numeric(sample_tb[[i]])
    }
  }
  
  for (i in c('depth_dating', 'corr_age', 'corr_age_uncert_neg', 'corr_age_uncert_pos')){
    if (class(dating_tb[[i]]) != 'numeric'){
      writeLines(paste('Somehow ', i, ' in Dating information table is not read as numeric. This rarely occurs (if it truly is not numeric, it should have been caught by the python checks first). This column will be coverted to numeric where possible. Please see that there is no warning and please mention this in the email when sending the workbook', sep = ''))
      dating_tb[[i]] <- as.numeric(dating_tb[[i]])
    }
  }
  
  if (dim(dating_lamina_tb)[1] > 0){
    for (i in c('depth_lam', 'lam_age')){
      if (class(dating_lamina_tb[[i]]) != 'numeric'){
        writeLines(paste('Somehow ', i, ' in Lamina age vs depth table is not read as numeric. This rarely occurs (if it truly is not numeric, it should have been caught by the python checks first). This column will be coverted to numeric where possible. Please see that there is no warning and please mention this in the email when sending the workbook', sep = ''))
        dating_lamina_tb[[i]] <- as.numeric(dating_lamina_tb[[i]])
      }
    }
  }
  
  
  # Plot models -------------------------------------------------------------------####
  # create a list of entity names
  entity_name_list <- unique(entity_tb$entity_name)
  entity_name_list <- entity_name_list[!is.na(entity_name_list)]
  grp_ctr = 1
  # loop through each entity
  p_temp <- ggplot() + theme_bw() + theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank())
  for (i in entity_name_list){
    writeLines(i) # print out entity name
    entity_name              <- i
    speleothem_type          <- entity_tb$speleothem_type[entity_tb$entity_name == i]
    contact_name             <- entity_tb$contact[entity_tb$entity_name == i]
    sample_from_entity       <- subset(sample_tb, entity_name == i)
    dating_for_entity        <- subset(dating_tb, entity_name == i)
    depth_ref                <- entity_tb$depth_ref[entity_tb$entity_name == i]
    dating_lamina_for_entity <- subset(dating_lamina_tb, entity_name == i)
    sample_from_entity$grp  <- NA # MW added to initialise in the event of H in position 1
    for (k in 1:dim(sample_from_entity)[1]){
      if (is.na(sample_from_entity[k,'gap']) & is.na(sample_from_entity[k,'hiatus'])){
        sample_from_entity$grp[k] = toString(grp_ctr)
      } else {
        grp_ctr = grp_ctr + 1
      }
    }
    sample_entity_hiatus <- subset(sample_from_entity, hiatus == "H")
    sample_from_entity <- subset(sample_from_entity, is.na(gap))
    sample_from_entity <- subset(sample_from_entity, is.na(hiatus))
    dating_present <- F
    sample_present <- F
    if (dim(dating_for_entity)[1] > 1){
      dating_present <- T
      dating_for_entity_NA <- dating_for_entity[is.na(dating_for_entity$date_used),]
      dating_for_entity_NotNo <- dating_for_entity[!is.na(dating_for_entity$date_used) & dating_for_entity$date_used != 'no',]
      dating_for_entity <- rbind(dating_for_entity_NA, dating_for_entity_NotNo)
      dating_for_entity <- subset(dating_for_entity, date_type != 'Event; hiatus' & date_type != 'Event; gap (composite record)')
      dating_for_entity <- Age_corrected2reference(dating_for_entity, old_age_columns = 'corr_age', dating = TRUE)
      if (dim(dating_lamina_for_entity)[1] > 0){
        dating_lamina_for_entity <- Age_corrected2reference(dating_lamina_for_entity, old_age_columns = 'lam_age')
      }
    } else {
      writeLines(paste('No dating information for', entity_name))
    }
    if (dim(sample_from_entity)[1] > 1){
      sample_present <- T
      if (length(sample_from_entity$interp_age[!is.na(sample_from_entity$interp_age)]) > 0){
        sample_from_entity <- Age_corrected2reference(sample_from_entity, dating_table = dating_tb)
      } else {
        sample_from_entity$Age_corrected2reference <- NA
      }
    } else {
      writeLines(paste('No sample data for', entity_name))
    }
    if (sample_present == T){
      if (dim(sample_from_entity[!is.na(sample_from_entity$Age_corrected2reference),])[1] > 1){
        if (dating_present == T){
          if (dim(dating_for_entity[!is.na(dating_for_entity$Age_corrected2reference),])[1] > 1){
            dating_for_entity$upper = dating_for_entity$Age_corrected2reference + dating_for_entity$corr_age_uncert_pos
            dating_for_entity$lower = dating_for_entity$Age_corrected2reference - dating_for_entity$corr_age_uncert_neg
            # 1. Plot age model -------------------------------------------------------####
            p <- ggplot() +
              geom_point(data=dating_for_entity, aes(x = Age_corrected2reference/1000, y = depth_dating)) +
              geom_errorbarh(data=dating_for_entity, aes(y = depth_dating, xmin = lower/1000,
                                                         xmax = upper/1000)) +
              geom_path(data = sample_from_entity, aes(x = Age_corrected2reference/1000, y = depth_sample, group = grp)) +
              xlab('Age (ka b2k)') + 
              ylab(paste('Distance ', depth_ref, ' (mm)')) +
              geom_hline(mapping = aes(yintercept = sample_entity_hiatus[['depth_sample']], colour = rep('hiatuses in workbook', length(sample_entity_hiatus[['depth_sample']]))), linetype = 'dotted', show.legend = T) +
              scale_x_reverse() +
              ggtitle(paste('Agemodel for ', entity_name, ' (', contact_name, ')', sep = '')) +
              theme(legend.title = element_blank())
            if (depth_ref == 'from top'){
              p <- p + scale_y_reverse()
            }
            if (depth_ref == 'from base'){
              sample_from_entity <- sample_from_entity[rev(order(sample_from_entity$depth_sample)),]
            } else {
              sample_from_entity <- sample_from_entity[order(sample_from_entity$depth_sample),]
            }
            if (dim(dating_lamina_for_entity)[1] > 0){
              p <- p + geom_point(data = dating_lamina_for_entity, aes(x = Age_corrected2reference/1000, y = depth_lam, colour = 'lamina in lamina age vs depth table')) +
                geom_path(data = sample_from_entity, aes(x = Age_corrected2reference/1000, y = depth_sample, group = grp, colour = 'samples in sample table')) +
                scale_colour_manual(values = c('red', 'blue','black'))
            }
            a <- sample_from_entity[['depth_sample']]
            sample_midpoint <- a[-length(a)] + diff(a)/2
            interp_age_diff <- diff(sample_from_entity[['Age_corrected2reference']])
            dt <- data.frame(depth = sample_midpoint, interp_age_diff = interp_age_diff)
            # 2. Plot possible hiatus plots -------------------------------------------####
            p1 <- ggplot() +
              geom_line(data = dt, aes(x = sample_midpoint, y = interp_age_diff)) + 
              xlab(paste0('Sample depth midpoints ', depth_ref,' (mm)')) + 
              ylab('Difference in interpolated ages between consecutive sample')
            # ggtitle(paste('Plot age differences between depths; ,', entity_name, '; dotted line shows hiatuses already identified in workbook'))
            if (dim(sample_entity_hiatus)[1] > 0){
              p1 <- p1 + geom_vline(xintercept = sample_entity_hiatus[['depth_sample']], linetype = 'dotted', colour = 'red')
            }
          } else {
            text2print1 <- paste('Entity ', entity_name, ' does not have dating information \n with valid dates. Age model plot cannot be made.', sep = '')
            p <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print1) 
            text2print2 <- paste('Entity ', entity_name, ' does not have dating information \n with valid dates. Possible hiatus plot cannot be made.', sep = '')
            p1 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print2)
          }
        } else if (speleothem_type == "composite") {
          # 1. Plot age model -------------------------------------------------------####
          p <- ggplot() +
            geom_path(data = sample_from_entity, aes(x = Age_corrected2reference/1000, y = depth_sample, group = grp)) +
            xlab('Age (ka b2k)') + 
            ylab(paste('Distance ', depth_ref, ' (mm)')) +
            geom_hline(mapping = aes(yintercept = sample_entity_hiatus[['depth_sample']], colour = rep('hiatuses in workbook', length(sample_entity_hiatus[['depth_sample']]))), linetype = 'dotted', show.legend = T) +
            scale_x_reverse() +
            ggtitle(paste('Agemodel for ', entity_name, ' (', contact_name, ')', sep = '')) +
            theme(legend.title = element_blank())
          if (depth_ref == 'from top'){
            p <- p + scale_y_reverse()
          }
          if (depth_ref == 'from base'){
            sample_from_entity <- sample_from_entity[rev(order(sample_from_entity$depth_sample)),]
          } else {
            sample_from_entity <- sample_from_entity[order(sample_from_entity$depth_sample),]
          }
          a <- sample_from_entity[['depth_sample']]
          sample_midpoint <- a[-length(a)] + diff(a)/2
          interp_age_diff <- diff(sample_from_entity[['Age_corrected2reference']])
          dt <- data.frame(depth = sample_midpoint, interp_age_diff = interp_age_diff)
          # 2. Plot possible hiatus plots -------------------------------------------####
          p1 <- ggplot() +
            geom_line(data = dt, aes(x = sample_midpoint, y = interp_age_diff)) + 
            xlab(paste0('Sample depth midpoints ', depth_ref,' (mm)')) + 
            ylab('Difference in interpolated ages between consecutive sample')
          # ggtitle(paste('Plot age differences between depths; ,', entity_name, '; dotted line shows hiatuses already identified in workbook'))
          if (dim(sample_entity_hiatus)[1] > 0){
            p1 <- p1 + geom_vline(xintercept = sample_entity_hiatus[['depth_sample']], linetype = 'dotted', colour = 'red')
          }
        } else {
          text2print1 <- paste('Entity ', entity_name, ' does not have dating information.\n Age model plot cannot be made.', sep = '')
          p <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print1)
          text2print2 <- paste('Entity ', entity_name, ' does not have dating information.\n Possible hiatus plot cannot be made.', sep = '')
          p1 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print2)
        }
        
        # 3. Plot d18O vs time if there is data
        p2_tb <- subset(sample_from_entity, (!is.na(d18O_measurement)))
        if (dim(p2_tb)[1] > 0){
          p2 <- ggplot() +
            geom_point(data=p2_tb, aes(x = Age_corrected2reference/1000, y = d18O_measurement)) +
            geom_path(data = p2_tb, aes(x = Age_corrected2reference/1000, y = d18O_measurement, group = grp)) +
            xlab('Age (ka b2k)') + 
            ylab(paste('d18O (permil)')) +
            scale_x_reverse() +
            ggtitle(paste('d18O vs time for ', entity_name, ' (', contact_name, ')', sep = '')) +
            theme(legend.title = element_blank())
        } else {
          text2print3 <- paste('Entity ', entity_name, ' does not have d18O data', sep = '')
          p2 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print3) 
        }
        # 4. Plot d13C vs time if there is data
        p3_tb <- subset(sample_from_entity, (!is.na(d13C_measurement)))
        if (dim(p3_tb)[1] > 0){
          p3 <- ggplot() +
            geom_point(data=p3_tb, aes(x = Age_corrected2reference/1000, y = d13C_measurement)) +
            geom_path(data = p3_tb, aes(x = Age_corrected2reference/1000, y = d13C_measurement, group = grp)) +
            xlab('Age (ka b2k)') + 
            ylab(paste('d13C (permil)')) +
            scale_x_reverse() +
            ggtitle(paste('d13C vs time for ', entity_name, ' (', contact_name, ')', sep = '')) +
            theme(legend.title = element_blank())
        } else {
          text2print4 <- paste('Entity ', entity_name, ' does not have d13C data.', sep = '')
          p3 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print4) 
        }
        # 4. Plot trace elements vs time if there is data
        p4_tb <- subset(sample_from_entity, (!is.na(Sr_Ca_measurement)))
        if (dim(p4_tb)[1] > 0){
          p4 <- ggplot() +
            geom_point(data=p4_tb, aes(x = Age_corrected2reference/1000, y = Sr_Ca_measurement)) +
            geom_path(data = p4_tb, aes(x = Age_corrected2reference/1000, y = Sr_Ca_measurement, group = grp)) +
            xlab('Age (ka b2k)') + 
            ylab(paste('Sr/Ca (mmol/mol)')) +
            scale_x_reverse() +
            ggtitle(paste('Sr/Ca vs time for ', entity_name, ' (', contact_name, ')', sep = '')) +
            theme(legend.title = element_blank())
        } else {
          text2print5 <- paste('Entity ', entity_name, ' does not have Sr/Ca data.', sep = '')
          p4 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print5) 
        }
        # 5. Plot trace elements vs time if there is data
        p5_tb <- subset(sample_from_entity, (!is.na(Mg_Ca_measurement)))
        if (dim(p5_tb)[1] > 0){
          p5 <- ggplot() +
            geom_point(data=p5_tb, aes(x = Age_corrected2reference/1000, y = Mg_Ca_measurement)) +
            geom_path(data = p5_tb, aes(x = Age_corrected2reference/1000, y = Mg_Ca_measurement, group = grp)) +
            xlab('Age (ka b2k)') + 
            ylab(paste('Mg/Ca (mmol/mol)')) +
            scale_x_reverse() +
            ggtitle(paste('Mg/Ca vs time for ', entity_name, ' (', contact_name, ')', sep = '')) +
            theme(legend.title = element_blank())
        } else {
          text2print6 <- paste('Entity ', entity_name, ' does not have Mg/Ca data.', sep = '')
          p5 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print6) 
        }
        # 6. Plot trace elements vs time if there is data
        p6_tb <- subset(sample_from_entity, (!is.na(Ba_Ca_measurement)))
        if (dim(p6_tb)[1] > 0){
          p6 <- ggplot() +
            geom_point(data=p6_tb, aes(x = Age_corrected2reference/1000, y = Ba_Ca_measurement)) +
            geom_path(data = p6_tb, aes(x = Age_corrected2reference/1000, y = Ba_Ca_measurement, group = grp)) +
            xlab('Age (ka b2k)') + 
            ylab(paste('Ba/Ca (mmol/mol)')) +
            scale_x_reverse() +
            ggtitle(paste('Ba/Ca vs time for ', entity_name, ' (', contact_name, ')', sep = '')) +
            theme(legend.title = element_blank())
        } else {
          text2print7 <- paste('Entity ', entity_name, ' does not have Ba/Ca data.', sep = '')
          p6 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print7) 
        }
        # 7. Plot trace elements vs time if there is data
        p7_tb <- subset(sample_from_entity, (!is.na(U_Ca_measurement)))
        if (dim(p7_tb)[1] > 0){
          p7 <- ggplot() +
            geom_point(data=p7_tb, aes(x = Age_corrected2reference/1000, y = U_Ca_measurement)) +
            geom_path(data = p7_tb, aes(x = Age_corrected2reference/1000, y = U_Ca_measurement, group = grp)) +
            xlab('Age (ka b2k)') + 
            ylab(paste('U/Ca (mmol/mol)')) +
            scale_x_reverse() +
            ggtitle(paste('U/Ca vs time for ', entity_name, ' (', contact_name, ')', sep = '')) +
            theme(legend.title = element_blank())
        } else {
          text2print8 <- paste('Entity ', entity_name, ' does not have U/Ca data.', sep = '')
          p7 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print8) 
        }
        # 8. Plot trace elements vs time if there is data
        p8_tb <- subset(sample_from_entity, (!is.na(P_Ca_measurement)))
        if (dim(p8_tb)[1] > 0){
          p8 <- ggplot() +
            geom_point(data=p8_tb, aes(x = Age_corrected2reference/1000, y = P_Ca_measurement)) +
            geom_path(data = p8_tb, aes(x = Age_corrected2reference/1000, y = P_Ca_measurement, group = grp)) +
            xlab('Age (ka b2k)') + 
            ylab(paste('P/Ca (mmol/mol)')) +
            scale_x_reverse() +
            ggtitle(paste('P/Ca vs time for ', entity_name, ' (', contact_name, ')', sep = '')) +
            theme(legend.title = element_blank())
        } else {
          text2print9 <- paste('Entity ', entity_name, ' does not have P/Ca data.', sep = '')
          p8 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print9) 
        }
        # 9. Plot trace elements vs time if there is data
        p9_tb <- subset(sample_from_entity, (!is.na(Sr_isotopes_measurement)))
        if (dim(p9_tb)[1] > 0){
          p9 <- ggplot() +
            geom_point(data=p9_tb, aes(x = Age_corrected2reference/1000, y = Sr_isotopes_measurement)) +
            geom_path(data = p9_tb, aes(x = Age_corrected2reference/1000, y = Sr_isotopes_measurement, group = grp)) +
            xlab('Age (ka b2k)') + 
            ylab(paste('Sr isotopes (mmol/mol)')) +
            scale_x_reverse() +
            ggtitle(paste('Sr isotopes vs time for ', entity_name, ' (', contact_name, ')', sep = '')) +
            theme(legend.title = element_blank())
        } else {
          text2print10 <- paste('Entity ', entity_name, ' does not have Sr isotopes data.', sep = '')
          p9 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print10) 
        }
      } else {
        p_temp <- ggplot() + theme_bw() + theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank())
        text2print1 <- paste('Entity ', entity_name, ' does not have sample data \n with valid dates. Age model plot cannot be made.', sep = '')
        p <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print1) 
        text2print2 <- paste('Entity ', entity_name, ' does not have sample data \n with valid dates. Possible hiatus plot cannot be made.', sep = '')
        p1 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print2)
        text2print3 <- paste('Entity ', entity_name, ' does not have sample data \n with valid dates. d18O vs age plot cannot be made.', sep = '')
        p2 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print3)
        text2print4 <- paste('Entity ', entity_name, ' does not have sample data \n with valid dates. d13C vs age plot cannot be made.', sep = '')
        p3 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print4)
        text2print5 <- paste('Entity ', entity_name, ' does not have sample data \n with valid dates. Sr/Ca vs age plot cannot be made.', sep = '')
        p4 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print5)
        text2print6 <- paste('Entity ', entity_name, ' does not have sample data \n with valid dates. Mg/Ca vs age plot cannot be made.', sep = '')
        p5 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print6)
        text2print7 <- paste('Entity ', entity_name, ' does not have sample data \n with valid dates. Ba/Ca vs age plot cannot be made.', sep = '')
        p6 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print7)
        text2print8 <- paste('Entity ', entity_name, ' does not have sample data \n with valid dates. U/Ca vs age plot cannot be made.', sep = '')
        p7 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print8)
        text2print9 <- paste('Entity ', entity_name, ' does not have sample data \n with valid dates. P/Ca vs age plot cannot be made.', sep = '')
        p8 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print9)
        text2print10 <- paste('Entity ', entity_name, ' does not have sample data \n with valid dates. Sr isotopes vs age plot cannot be made.', sep = '')
        p9 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print10)
      }
    } else {
      text2print1 <- paste('Entity ', entity_name, ' does not have sample data.\n Age model plot cannot be made.', sep = '')
      p <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print1) 
      text2print2 <- paste('Entity ', entity_name, ' does not have sample data.\n Possible hiatus plot cannot be made.', sep = '')
      p1 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print2)
      text2print3 <- paste('Entity ', entity_name, ' does not have sample data.\n d18O vs age plot cannot be made.', sep = '')
      p2 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print3)
      text2print4 <- paste('Entity ', entity_name, ' does not have sample data.\n d13C vs age plot cannot be made.', sep = '')
      p3 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print4)
      text2print5 <- paste('Entity ', entity_name, ' does not have sample data.\n Sr/Ca vs age plot cannot be made.', sep = '')
      p4 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print5)
      text2print6 <- paste('Entity ', entity_name, ' does not have sample data.\n Mg/Ca vs age plot cannot be made.', sep = '')
      p5 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print6)
      text2print7 <- paste('Entity ', entity_name, ' does not have sample data.\n Ba/Ca vs age plot cannot be made.', sep = '')
      p6 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print7)
      text2print8 <- paste('Entity ', entity_name, ' does not have sample data.\n U/Ca vs age plot cannot be made.', sep = '')
      p7 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print8)
      text2print9 <- paste('Entity ', entity_name, ' does not have sample data.\n P/Ca vs age plot cannot be made.', sep = '')
      p8 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print9)
      text2print10 <- paste('Entity ', entity_name, ' does not have sample data.\n Sr isotopes vs age plot cannot be made.', sep = '')
      p9 <- p_temp + annotate("text", x = 4, y = 25, size = 8, label = text2print10)
      
    }
    # print to pdf
    pdf(paste(pth, '/QC_agemodel_hiatus_', unlist(strsplit(site_tb$site_name, " ", fixed = T))[1], "_", entity_name,'.pdf', sep = ''), 10, 8)
    print(p)
    print(p1)
    print(p2)
    print(p3)
    print(p4)
    print(p5)
    print(p6)
    print(p7)
    print(p8)
    print(p9)
    dev.off()
  }
}